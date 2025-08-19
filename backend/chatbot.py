import os
import pickle
import json
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from flask import Blueprint, request, jsonify
import pandas as pd
from model.train_and_export_category_model import pipeline as category_model
from datetime import datetime, timedelta
from pymongo import MongoClient
from bson import ObjectId
import re
from anomaly_detection import anomaly_detector

# Import Groq
from groq import Groq

chatbot_bp = Blueprint('chatbot', __name__)

# Initialize Groq client
GROQ_API_KEY = "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"
groq_client = Groq(api_key=GROQ_API_KEY)

# Configure requests session with retry logic
session = requests.Session()
retries = Retry(
    total=5,
    backoff_factor=1,
    status_forcelist=[500, 502, 503, 504],
    allowed_methods=["POST"]
)
session.mount("https://", HTTPAdapter(max_retries=retries))

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['biguard']
users_collection = db['users']
accounts_collection = db['accounts']
transactions_collection = db['transactions']
budgets_collection = db['budgets']
conversations_collection = db['conversations']  # New collection for conversation history

# Load the trained category classifier model (if not already loaded)
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'category_classifier.pkl')
if os.path.exists(MODEL_PATH):
    with open(MODEL_PATH, 'rb') as f:
        category_model = pickle.load(f)
else:
    category_model = None

# Load Q&A dataset
qa_dataset = None
def load_qa_dataset():
    """Load the Q&A dataset from CSV file"""
    global qa_dataset
    try:
        csv_path = os.path.join(os.path.dirname(__file__), 'biguard_chatbot_qna_1000.csv')
        if os.path.exists(csv_path):
            qa_dataset = pd.read_csv(csv_path)
            print(f"Loaded {len(qa_dataset)} Q&A pairs from dataset")
            return qa_dataset
        else:
            print("Q&A dataset not found")
            return None
    except Exception as e:
        print(f"Error loading Q&A dataset: {e}")
        return None

# Load the dataset when module is imported
qa_dataset = load_qa_dataset()

def find_best_match(user_question, qa_data):
    """Find the best matching question from the Q&A dataset with improved matching"""
    if qa_data is None or len(qa_data) == 0:
        return None, None
    
    user_question_lower = user_question.lower().strip()
    
    # Simple keyword matching with improved logic
    best_match = None
    best_score = 0
    
    for _, row in qa_data.iterrows():
        question = str(row['Question']).lower().strip()
        answer = str(row['Answer']).strip()
        
        # Calculate similarity score
        score = 0
        
        # Exact match gets highest score
        if user_question_lower == question:
            score = 100
        # Contains all words (improved)
        elif all(word in question for word in user_question_lower.split() if len(word) > 2):
            score = 85
        # Contains most words (70%+ match)
        elif sum(1 for word in user_question_lower.split() if len(word) > 2 and word in question) >= len([w for w in user_question_lower.split() if len(w) > 2]) * 0.7:
            score = 70
        # Contains key financial terms
        elif any(term in question for term in ['savings', 'checking', 'account', 'budget', 'spending', 'category', 'plaid', 'fraud']):
            if any(term in user_question_lower for term in ['savings', 'checking', 'account', 'budget', 'spending', 'category', 'plaid', 'fraud']):
                score = 60
        # Contains some key words
        elif any(word in question for word in user_question_lower.split() if len(word) > 3):
            score = 40
        
        if score > best_score:
            best_score = score
            best_match = (question, answer)
    
    return best_match if best_score > 35 else None

def extract_transaction_info(user_message):
    """Extract transaction name and amount from user message"""
    # Look for patterns like "Starbucks $5.75" or "Netflix 15.99"
    patterns = [
        r'(\w+(?:\s+\w+)*)\s+\$?(\d+\.?\d*)',  # "Starbucks $5.75"
        r'\$?(\d+\.?\d*)\s+(\w+(?:\s+\w+)*)',  # "$5.75 Starbucks"
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, user_message, re.IGNORECASE)
        if matches:
            # Return the first match
            if len(matches[0]) == 2:
                return matches[0][0], float(matches[0][1])
    
    return None, None

# Enhanced financial knowledge base
FINANCIAL_KNOWLEDGE = """
Financial Management Basics:

**Account Types:**
- Checking Account: Used for daily transactions, bill payments, and ATM withdrawals. Usually has lower interest rates but high liquidity.
- Savings Account: Designed for saving money with higher interest rates. Limited transactions per month, better for long-term savings.

**Budgeting:**
- The 50/30/20 rule: 50% for needs, 30% for wants, 20% for savings
- Track all income and expenses to create an effective budget
- Common categories: Food & Dining, Transportation, Entertainment, Shopping, Utilities, Healthcare, Education, Travel, Insurance, Investments

**Saving Money:**
- Build an emergency fund of 3-6 months of expenses
- Use automatic transfers to make saving easier
- Consider high-yield savings accounts for better returns

**Credit Score:**
- Ranges from 300-850
- Factors: Payment history (35%), Credit utilization (30%), Length of credit history (15%), Credit mix (10%), New credit (10%)

**Investment Basics:**
- Diversification reduces risk
- Consider: stocks, bonds, mutual funds, ETFs, retirement accounts (401(k), IRA)
- Start early to benefit from compound interest

**Debt Management:**
- Prioritize high-interest debt first
- Consider debt consolidation or balance transfers
- Always pay more than minimum payments

**Fraud Prevention:**
- Monitor accounts regularly
- Use strong passwords and two-factor authentication
- Never share personal information with unknown sources
- Report suspicious activity immediately

**Financial Goals:**
- Set SMART goals: Specific, Measurable, Achievable, Relevant, Time-bound
- Examples: Emergency fund, debt payoff, home purchase, retirement planning
"""

def save_conversation(user_id, user_message, bot_response):
    """Save conversation to MongoDB for memory"""
    try:
        conversation = {
            'user_id': str(user_id),
            'user_message': user_message,
            'bot_response': bot_response,
            'timestamp': datetime.now(),
            'date': datetime.now().strftime('%Y-%m-%d')
        }
        conversations_collection.insert_one(conversation)
        return True
    except Exception as e:
        print(f"Error saving conversation: {e}")
        return False

def get_conversation_history(user_id, limit=10):
    """Get recent conversation history for context"""
    try:
        conversations = list(conversations_collection.find(
            {'user_id': str(user_id)}
        ).sort('timestamp', -1).limit(limit))
        
        # Format conversations for context
        history = []
        for conv in reversed(conversations):  # Reverse to get chronological order
            history.append(f"User: {conv['user_message']}")
            history.append(f"Assistant: {conv['bot_response']}")
        
        return history
    except Exception as e:
        print(f"Error getting conversation history: {e}")
        return []

def get_user_financial_context(user_id):
    """Get user's financial context for AI responses"""
    try:
        # First, check if user has sample data or real data
        user = users_collection.find_one({'_id': ObjectId(user_id)})
        has_sample_data = user.get('has_sample_data', False) if user else False
        
        # Build query filters based on data type
        if has_sample_data:
            # User has sample data - only show sample transactions
            transaction_filter = {'user_id': str(user_id), 'is_sample': True}
            account_filter = {'user_id': str(user_id), 'is_sample': True}
            budget_filter = {'user_id': str(user_id), 'is_sample': True}
            data_type = "sample"
        else:
            # User has real data - exclude sample data
            transaction_filter = {'user_id': str(user_id), 'is_sample': {'$ne': True}}
            account_filter = {'user_id': str(user_id), 'is_sample': {'$ne': True}}
            budget_filter = {'user_id': str(user_id), 'is_sample': {'$ne': True}}
            data_type = "real"
        
        # Get ALL user's transactions with proper filtering (no limit)
        recent_transactions = list(transactions_collection.find(
            transaction_filter
        ).sort('date', -1))
        
        # Get user's budgets with proper filtering
        user_budgets = list(budgets_collection.find(budget_filter))
        
        # Get user's accounts with proper filtering
        user_accounts = list(accounts_collection.find(account_filter))
        
        # Calculate current month stats
        now = datetime.now()
        start_date = now.replace(day=1).strftime('%Y-%m-%d')
        end_date = now.strftime('%Y-%m-%d')
        
        monthly_transactions = [t for t in recent_transactions 
                              if start_date <= t.get('date', '') <= end_date]
        
        total_spent = sum(t['amount'] for t in monthly_transactions if t.get('is_expense', True))
        total_income = sum(t['amount'] for t in monthly_transactions if not t.get('is_expense', True))
        
        # Category breakdown
        category_totals = {}
        for t in monthly_transactions:
            cat = t.get('category', 'Uncategorized')
            category_totals[cat] = category_totals.get(cat, 0) + abs(t['amount'])
        
        # Budget status
        budget_status = {}
        for budget in user_budgets:
            category = budget['category']
            budget_amount = budget['amount']
            spent = category_totals.get(category, 0)
            percentage = (spent / budget_amount * 100) if budget_amount > 0 else 0
            budget_status[category] = {
                'budget': budget_amount,
                'spent': spent,
                'remaining': budget_amount - spent,
                'percentage': percentage
            }
        
        # Spending patterns analysis
        spending_patterns = analyze_spending_patterns(recent_transactions)
        
        return {
            'recent_transactions': recent_transactions,  # All transactions, not just 20
            'monthly_transactions': monthly_transactions,  # Add monthly transactions for detailed analysis
            'all_transactions': recent_transactions,  # Add all transactions for comprehensive analysis
            'monthly_spending': total_spent,
            'monthly_income': total_income,
            'category_breakdown': category_totals,
            'budget_status': budget_status,
            'accounts': user_accounts,
            'current_balance': sum(a.get('current_balance', 0) for a in user_accounts),
            'spending_patterns': spending_patterns,
            'data_type': data_type  # Add data type to context
        }
    except Exception as e:
        print(f"Error getting financial context: {e}")
        return {}

def analyze_spending_patterns(transactions):
    """Analyze spending patterns and provide insights"""
    try:
        if not transactions:
            return {}
        
        # Calculate spending by category
        category_spending = {}
        for t in transactions:
            if t.get('is_expense', True):
                cat = t.get('category', 'Uncategorized')
                category_spending[cat] = category_spending.get(cat, 0) + abs(t['amount'])
        
        # Find top spending categories
        top_categories = sorted(category_spending.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Calculate average transaction amount
        expense_transactions = [t for t in transactions if t.get('is_expense', True)]
        if expense_transactions:
            avg_amount = sum(abs(t['amount']) for t in expense_transactions) / len(expense_transactions)
        else:
            avg_amount = 0
        
        # Find unusual transactions (more than 2x average)
        unusual_transactions = [t for t in transactions if abs(t['amount']) > avg_amount * 2] if avg_amount > 0 else []
        
        # Analyze spending frequency
        spending_frequency = {}
        for t in transactions:
            if t.get('is_expense', True):
                cat = t.get('category', 'Uncategorized')
                spending_frequency[cat] = spending_frequency.get(cat, 0) + 1
        
        return {
            'top_spending_categories': top_categories,
            'average_transaction_amount': avg_amount,
            'unusual_transactions': unusual_transactions[:5],
            'spending_frequency': spending_frequency,
            'total_categories': len(category_spending)
        }
    except Exception as e:
        print(f"Error analyzing spending patterns: {e}")
        return {}

def generate_financial_advice(financial_context):
    """Generate personalized financial advice based on user data"""
    try:
        advice = []
        
        if not financial_context:
            return ["I don't have enough data to provide personalized advice yet. Please connect your accounts and add some transactions."]
        
        monthly_spending = financial_context.get('monthly_spending', 0)
        monthly_income = financial_context.get('monthly_income', 0)
        category_breakdown = financial_context.get('category_breakdown', {})
        budget_status = financial_context.get('budget_status', {})
        spending_patterns = financial_context.get('spending_patterns', {})
        
        # Income vs Spending Analysis
        if monthly_income > 0:
            spending_ratio = monthly_spending / monthly_income
            if spending_ratio > 0.9:
                advice.append("⚠️ **High Spending Alert**: You're spending over 90% of your income. Consider reducing expenses or increasing income.")
            elif spending_ratio > 0.8:
                advice.append("⚠️ **Spending Warning**: You're spending over 80% of your income. Try to save at least 20% of your income.")
            elif spending_ratio < 0.5:
                advice.append("✅ **Great Job**: You're spending less than 50% of your income. Consider investing the surplus.")
        
        # Budget Analysis
        for category, status in budget_status.items():
            if status['percentage'] > 100:
                advice.append(f"🚨 **Budget Exceeded**: You've exceeded your {category} budget by ${status['spent'] - status['budget']:.2f}")
            elif status['percentage'] > 80:
                advice.append(f"⚠️ **Budget Warning**: You're close to your {category} budget limit. ${status['remaining']:.2f} remaining.")
        
        # Spending Pattern Analysis
        top_categories = spending_patterns.get('top_spending_categories', [])
        if top_categories:
            top_category, top_amount = top_categories[0]
            if top_amount > monthly_spending * 0.4:
                advice.append(f"💡 **Spending Insight**: {top_category} accounts for over 40% of your spending. Consider if this aligns with your financial goals.")
        
        # Savings Recommendation
        if monthly_income > monthly_spending:
            potential_savings = monthly_income - monthly_spending
            advice.append(f"💰 **Savings Opportunity**: You could save ${potential_savings:.2f} per month. Consider setting up automatic transfers.")
        
        # Emergency Fund Check
        current_balance = financial_context.get('current_balance', 0)
        if current_balance < monthly_spending * 3:
            advice.append("🛡️ **Emergency Fund**: Consider building an emergency fund of 3-6 months of expenses for financial security.")
        
        return advice if advice else ["Your financial situation looks good! Keep up the great work managing your money."]
        
    except Exception as e:
        print(f"Error generating financial advice: {e}")
        return ["I'm having trouble analyzing your financial data. Please try again later."]

def query_groq_api(prompt: str) -> str:
    """Query the Groq API for answers based on the prompt."""
    try:
        if not GROQ_API_KEY or GROQ_API_KEY.strip() == "":
            return "Error: GROQ_API_KEY not set."

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        }
        data = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": "You are BiGuard AI, a helpful financial assistant. Provide accurate, concise, and actionable financial advice. Use markdown formatting for better readability."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 500,
            "temperature": 0.7,
            "top_p": 0.9,
        }

        response = session.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data, timeout=30)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Groq API: {str(e)}")
        return "I apologize, but I'm having trouble connecting to the AI service. Please try again later."
    except Exception as e:
        print(f"An unexpected error occurred in query_groq_api: {str(e)}")
        return "An internal error occurred."

def generate_ai_response(user_message, user_id, financial_context):
    """Generate AI response using Groq API with financial context, conversation history, and Q&A dataset as reference"""
    try:
        # Get conversation history for context
        conversation_history = get_conversation_history(user_id, limit=5)
        
        # Prepare context for the AI
        context_parts = []
        
        # Add conversation history context
        if conversation_history:
            context_parts.append("**Recent Conversation History:**")
            context_parts.extend(conversation_history[-6:])  # Last 3 exchanges
            context_parts.append("")  # Empty line for separation
        
        if financial_context:
            # Add comprehensive financial summary
            context_parts.append(f"**User's Complete Financial Summary:**")
            context_parts.append(f"- Total Spending (This Month): ${financial_context.get('monthly_spending', 0):.2f}")
            context_parts.append(f"- Total Income (This Month): ${financial_context.get('monthly_income', 0):.2f}")
            context_parts.append(f"- Current Balance: ${financial_context.get('current_balance', 0):.2f}")
            
            # Add account information
            if financial_context.get('accounts'):
                context_parts.append(f"\n**User's Accounts:**")
                for account in financial_context['accounts']:
                    account_name = account.get('name', 'Unknown Account')
                    account_type = account.get('subtype', account.get('type', 'Unknown'))
                    balance = account.get('current_balance', 0)
                    context_parts.append(f"- {account_name} ({account_type}): ${balance:.2f}")
            
            # Add category breakdown
            if financial_context.get('category_breakdown'):
                context_parts.append("\n**Spending by Category (This Month):**")
                for category, amount in financial_context['category_breakdown'].items():
                    context_parts.append(f"- {category}: ${amount:.2f}")
            
            # Add ALL transactions for comprehensive analysis
            if financial_context.get('all_transactions'):
                context_parts.append(f"\n**Complete Transaction History ({len(financial_context['all_transactions'])} transactions):**")
                # Sort by amount (highest first) for easy identification of most expensive
                sorted_transactions = sorted(
                    financial_context['all_transactions'], 
                    key=lambda x: abs(x.get('amount', 0)), 
                    reverse=True
                )
                for i, transaction in enumerate(sorted_transactions[:20]):  # Show top 20 transactions
                    amount = transaction.get('amount', 0)
                    name = transaction.get('name', 'Unknown')
                    category = transaction.get('category', 'Uncategorized')
                    date = transaction.get('date', 'Unknown')
                    is_expense = transaction.get('is_expense', True)
                    sign = "-" if is_expense else "+"
                    context_parts.append(f"{i+1}. {name} ({category}) - {date}: {sign}${abs(amount):.2f}")
            
            # Add monthly transactions specifically
            if financial_context.get('monthly_transactions'):
                context_parts.append(f"\n**Current Month Transactions ({len(financial_context['monthly_transactions'])} transactions):**")
                # Sort by amount (highest first) for easy identification of most expensive
                sorted_monthly = sorted(
                    financial_context['monthly_transactions'], 
                    key=lambda x: abs(x.get('amount', 0)), 
                    reverse=True
                )
                for i, transaction in enumerate(sorted_monthly[:15]):  # Show top 15 monthly transactions
                    amount = transaction.get('amount', 0)
                    name = transaction.get('name', 'Unknown')
                    category = transaction.get('category', 'Uncategorized')
                    date = transaction.get('date', 'Unknown')
                    is_expense = transaction.get('is_expense', True)
                    sign = "-" if is_expense else "+"
                    context_parts.append(f"{i+1}. {name} ({category}) - {date}: {sign}${abs(amount):.2f}")
            
            # Add budget status
            if financial_context.get('budget_status'):
                context_parts.append("\n**Budget Status:**")
                for category, status in financial_context['budget_status'].items():
                    if status['percentage'] > 100:
                        context_parts.append(f"- {category}: EXCEEDED (${status['spent']:.2f} / ${status['budget']:.2f})")
                    elif status['percentage'] > 80:
                        context_parts.append(f"- {category}: WARNING (${status['spent']:.2f} / ${status['budget']:.2f})")
                    else:
                        context_parts.append(f"- {category}: Good (${status['spent']:.2f} / ${status['budget']:.2f})")
            
            # Add spending patterns analysis
            if financial_context.get('spending_patterns'):
                patterns = financial_context['spending_patterns']
                context_parts.append(f"\n**Spending Analysis:**")
                context_parts.append(f"- Average Transaction Amount: ${patterns.get('average_transaction_amount', 0):.2f}")
                context_parts.append(f"- Total Categories: {patterns.get('total_categories', 0)}")
                if patterns.get('top_spending_categories'):
                    context_parts.append(f"- Top Spending Categories:")
                    for category, amount in patterns['top_spending_categories'][:3]:
                        context_parts.append(f"  • {category}: ${amount:.2f}")
        
        # Add relevant Q&A context based on user's question
        qa_context = ""
        if qa_dataset is not None:
            # Find relevant Q&A pairs for context
            relevant_qa = []
            user_question_lower = user_message.lower()
            
            for _, row in qa_dataset.iterrows():
                question = str(row['Question']).lower()
                answer = str(row['Answer'])
                
                # Check if Q&A is relevant to user's question
                if any(term in question for term in ['savings', 'checking', 'account', 'budget', 'plaid']) and any(term in user_question_lower for term in ['savings', 'checking', 'account', 'budget', 'plaid']):
                    relevant_qa.append(f"Q: {row['Question']}\nA: {answer}")
                elif any(term in question for term in ['category', 'starbucks', 'netflix', 'uber']) and any(term in user_question_lower for term in ['category', 'starbucks', 'netflix', 'uber']):
                    relevant_qa.append(f"Q: {row['Question']}\nA: {answer}")
            
            if relevant_qa:
                qa_context = "\n\n**Relevant Q&A Context:**\n" + "\n\n".join(relevant_qa[:3])  # Limit to 3 most relevant
        
        # Add data type context
        data_type = financial_context.get('data_type', 'unknown')
        data_context = ""
        if data_type == "sample":
            data_context = "\n**IMPORTANT:** The user is currently using SAMPLE/DEMO data for testing purposes. This is not their real financial data. When providing advice, mention that this is based on sample data and they should connect their real bank account for personalized insights."
        elif data_type == "real":
            data_context = "\n**IMPORTANT:** The user is using their REAL financial data from their connected bank accounts. Provide personalized advice based on their actual financial situation."
        
        # Create the system prompt
        system_prompt = f"""You are BiGuard AI, a helpful financial assistant. You help users understand their finances, provide budgeting advice, and answer questions about their transactions and spending patterns.

**IMPORTANT: You have access to the user's COMPLETE financial data including:**
- All transactions (complete history)
- Current month transactions
- Account balances and details
- Budget information and status
- Spending patterns and analysis
- Category breakdowns

{chr(10).join(context_parts) if context_parts else ''}

{qa_context}

{data_context}

**Financial Knowledge Base:**
{FINANCIAL_KNOWLEDGE}

**Key Capabilities:**
1. Transaction categorization and analysis
2. Budget tracking and recommendations
3. Spending pattern insights
4. Financial goal planning
5. Fraud detection alerts
6. General financial advice

**Important Instructions:**
- You have access to ALL the user's financial data - use it comprehensively
- For questions about specific transactions, refer to the complete transaction history provided
- For questions about spending patterns, use the spending analysis data
- For questions about budgets, use the budget status information
- For questions about accounts, use the account information provided
- Use the conversation history to understand the user's context and previous questions
- Reference previous conversations when relevant to provide continuity
- Use the Q&A context above as reference, but provide your own comprehensive and intelligent answers
- Don't just repeat the Q&A answers - expand on them with additional insights
- For questions about account differences, provide detailed explanations
- Always be helpful, accurate, and provide actionable advice
- Use the financial context provided to give personalized responses based on their actual data
- Keep responses concise but informative
- Use bullet points when appropriate for better readability
- Format important information with **bold** text
- Make responses personal and specific to this user's financial situation
- If the user is using sample data, remind them that this is demo data and encourage them to connect their real bank account for personalized insights
- When asked about specific transactions, amounts, or spending, provide exact figures from the data provided"""

        # Create the user message
        user_prompt = f"User question: {user_message}"

        # Call Groq API
        response = query_groq_api(f"{system_prompt}\n\n{user_prompt}")
        return response
        
    except Exception as e:
        print(f"Error generating AI response: {e}")
        return "I'm having trouble processing your request right now. Please try again later."

def handle_specific_queries(user_message, user_id, financial_context):
    """Handle specific types of queries with custom logic"""
    message_lower = user_message.lower()
    
    # Handle specific financial questions with direct answers FIRST (before Q&A matching)
    if any(term in message_lower for term in ['savings', 'checking', 'account']):
        if 'difference' in message_lower or 'vs' in message_lower or 'between' in message_lower:
            return """**Checking vs Savings Accounts:**

**Checking Account:**
• Used for daily transactions and bill payments
• Usually has lower or no interest rates
• Unlimited transactions and ATM withdrawals
• High liquidity - easy access to money
• Often comes with debit cards

**Savings Account:**
• Designed for saving money with higher interest rates
• Limited transactions per month (usually 6)
• Better for long-term savings goals
• May have minimum balance requirements
• Great for emergency funds

**When to use each:**
- Use **checking** for daily expenses, bills, and regular spending
- Use **savings** for emergency funds, goals, and money you want to grow"""
    
    # Temporarily disable Q&A dataset to test Groq responses
    # qa_match = find_best_match(user_message, qa_dataset)
    # if qa_match:
    #     question, answer = qa_match
    #     return answer
    

    
    # Category prediction queries
    if any(keyword in message_lower for keyword in ['categorize', 'category', 'what category', 'classify']):
        if category_model:
            try:
                # Try to extract transaction info from the message
                transaction_name, amount = extract_transaction_info(user_message)
                
                if transaction_name and amount:
                    tx = {'name': transaction_name, 'amount': amount}
                    pred = category_model.predict(pd.DataFrame([tx]))[0]
                    return f"Based on the transaction '{transaction_name} ${amount}', this would likely be categorized as: **{pred}**"
                elif 'starbucks' in message_lower:
                    tx = {'name': 'Starbucks Coffee', 'amount': 5.75}
                    pred = category_model.predict(pd.DataFrame([tx]))[0]
                    return f"Based on the transaction 'Starbucks Coffee', this would likely be categorized as: **{pred}**"
                elif 'uber' in message_lower:
                    tx = {'name': 'Uber Ride', 'amount': 25.50}
                    pred = category_model.predict(pd.DataFrame([tx]))[0]
                    return f"Based on the transaction 'Uber Ride', this would likely be categorized as: **{pred}**"
                else:
                    return "I can help categorize transactions! Please provide the transaction name and amount, or ask about specific merchants like 'Starbucks' or 'Uber'."
            except Exception as e:
                return f"Error predicting category: {e}"
        else:
            return "I'm sorry, the categorization model isn't available right now."
    
    # Budget queries
    elif any(keyword in message_lower for keyword in ['budget', 'budgeting', 'spending limit']):
        if financial_context.get('budget_status'):
            budget_info = []
            for category, status in financial_context['budget_status'].items():
                if status['percentage'] > 100:
                    budget_info.append(f"🚨 **{category}**: Exceeded by ${status['spent'] - status['budget']:.2f}")
                elif status['percentage'] > 80:
                    budget_info.append(f"⚠️ **{category}**: ${status['remaining']:.2f} remaining")
                else:
                    budget_info.append(f"✅ **{category}**: ${status['remaining']:.2f} remaining")
            
            return f"**Your Current Budget Status:**\n\n" + "\n".join(budget_info)
        else:
            return "I don't see any budgets set up yet. You can create budgets in the Budgets section to track your spending by category."
    
    # Spending analysis queries
    elif any(keyword in message_lower for keyword in ['spending', 'expenses', 'how much', 'spent', 'top spending']):
        if financial_context.get('monthly_spending'):
            spending = financial_context['monthly_spending']
            income = financial_context.get('monthly_income', 0)
            net = income - spending
            
            response = f"**Your Spending Summary (This Month):**\n\n"
            response += f"💰 **Total Spending**: ${spending:.2f}\n"
            if income > 0:
                response += f"💵 **Total Income**: ${income:.2f}\n"
                response += f"📊 **Net**: ${net:.2f}\n"
            
            if financial_context.get('category_breakdown'):
                response += f"\n**Top Spending Categories:**\n"
                sorted_categories = sorted(financial_context['category_breakdown'].items(), 
                                        key=lambda x: x[1], reverse=True)[:5]
                for category, amount in sorted_categories:
                    response += f"• {category}: ${amount:.2f}\n"
            
            return response
        else:
            return "I don't have enough transaction data to analyze your spending yet. Try connecting your bank accounts or adding some transactions first."
    
    # Financial advice queries
    elif any(keyword in message_lower for keyword in ['advice', 'recommendation', 'suggestion', 'help me']):
        advice = generate_financial_advice(financial_context)
        return "**Personalized Financial Advice:**\n\n" + "\n".join([f"• {item}" for item in advice])
    
    # Fraud detection queries
    elif any(keyword in message_lower for keyword in ['fraud', 'suspicious', 'unusual', 'alert']):
        try:
            # Get user to determine data type
            user = users_collection.find_one({'_id': ObjectId(user_id)})
            data_type = 'sample' if user.get('has_sample_data', False) else 'real'
            
            # Get anomaly summary with correct data type
            anomaly_summary = anomaly_detector.get_anomaly_summary(user_id, data_type)
            
            if anomaly_summary['total_anomalies'] > 0:
                response = f"🚨 **Anomaly Detection Alert:**\n\n"
                response += f"**Risk Level:** {anomaly_summary['risk_level'].upper()}\n"
                response += f"**Total Anomalies:** {anomaly_summary['total_anomalies']}\n"
                response += f"**High Severity:** {anomaly_summary['high_severity']}\n"
                response += f"**Medium Severity:** {anomaly_summary['medium_severity']}\n"
                response += f"**Low Severity:** {anomaly_summary['low_severity']}\n\n"
                
                if anomaly_summary['recent_anomalies']:
                    response += "**Recent Suspicious Transactions:**\n"
                    for anomaly in anomaly_summary['recent_anomalies'][:3]:
                        tx = anomaly['transaction']
                        response += f"• {tx.get('name', 'Unknown')} - ${tx.get('amount', 0):.2f} on {tx.get('date', 'Unknown date')}\n"
                        response += f"  Reasons: {', '.join(anomaly['reasons'])}\n"
                
                response += "\n**Recommendations:**\n"
                if anomaly_summary['risk_level'] == 'high':
                    response += "• Contact your bank immediately\n"
                    response += "• Review all recent transactions\n"
                    response += "• Consider freezing your account\n"
                elif anomaly_summary['risk_level'] == 'medium':
                    response += "• Monitor your account closely\n"
                    response += "• Review suspicious transactions\n"
                    response += "• Update your security settings\n"
                else:
                    response += "• Continue monitoring your account\n"
                    response += "• Review flagged transactions\n"
                
                return response
            else:
                return "✅ No anomalies detected in your recent transactions. Your account appears to be secure!"
        except Exception as e:
            print(f"Error in fraud detection: {e}")
            return "I'm having trouble checking for fraud alerts right now. Please try again later."
    
    # Return None to use AI response
    return None

@chatbot_bp.route('/api/chatbot', methods=['POST'])
def chatbot():
    """Enhanced chatbot endpoint with user-specific memory, Q&A dataset and Groq AI integration"""
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        user_id = data.get('user_id')
        
        if not user_message.strip():
            return jsonify({'reply': 'Please provide a message to chat with me!'})
        
        if not user_id:
            return jsonify({'reply': 'User ID is required for personalized assistance. Please log in first.'})
        
        # Get user's financial context
        financial_context = get_user_financial_context(user_id)
        
        # Try to handle specific queries first (only for very specific cases)
        specific_response = handle_specific_queries(user_message, user_id, financial_context)
        
        if specific_response:
            reply = specific_response
        else:
            # Generate AI response using Groq (this is the primary response method)
            try:
                reply = generate_ai_response(user_message, user_id, financial_context)
                # Add fallback if response is too short or generic
                if len(reply) < 20 or reply in ["I'm having trouble processing your request right now. Please try again later.", "An internal error occurred."]:
                    reply = f"I understand you're asking about '{user_message}'. Let me provide you with some helpful information about this topic. You can also try asking more specific questions about budgeting, spending, or financial planning, and I'll do my best to help!"
            except Exception as e:
                print(f"Error in AI response generation: {e}")
                reply = f"I understand you're asking about '{user_message}'. While I'm processing your request, here are some general tips: You can ask me about transaction categorization, budget management, spending analysis, or general financial advice. What specific aspect would you like to know more about?"
        
        # Save the conversation for memory
        save_conversation(user_id, user_message, reply)
        
        return jsonify({'reply': reply})
        
    except Exception as e:
        print(f"Chatbot error: {e}")
        return jsonify({'reply': 'I encountered an error while processing your request. Please try again.'}), 500

@chatbot_bp.route('/api/chatbot/health', methods=['GET'])
def chatbot_health():
    """Health check endpoint for the chatbot"""
    try:
        # Test Groq API connection
        test_response = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": "Hello"}],
            model="llama3-8b-8192",
            max_tokens=10
        )
        
        return jsonify({
            'status': 'healthy',
            'groq_api': 'connected',
            'category_model': 'loaded' if category_model else 'not_loaded',
            'qa_dataset': f'loaded ({len(qa_dataset) if qa_dataset is not None else 0} pairs)' if qa_dataset is not None else 'not_loaded',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@chatbot_bp.route('/api/chatbot/financial-advice', methods=['GET'])
def get_financial_advice_endpoint():
    """Get personalized financial advice"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        financial_context = get_user_financial_context(user_id)
        advice = generate_financial_advice(financial_context)
        
        return jsonify({
            'advice': advice,
            'financial_summary': {
                'monthly_spending': financial_context.get('monthly_spending', 0),
                'monthly_income': financial_context.get('monthly_income', 0),
                'current_balance': financial_context.get('current_balance', 0)
            }
        })
    except Exception as e:
        print(f"Error getting financial advice: {e}")
        return jsonify({'error': 'Failed to generate financial advice'}), 500

@chatbot_bp.route('/api/chatbot/faq', methods=['GET'])
def get_faq():
    """Return the FAQ data for the chatbot."""
    return jsonify({
        "faq": [
            {
                "question": "What is the difference between a checking account and a savings account?",
                "answer": "A checking account is used for daily transactions, while a savings account is for saving money and earning interest."
            },
            {
                "question": "How can I set a budget for my monthly expenses?",
                "answer": "You can set a budget for each category like groceries, rent, etc., and the app will help track and remind you."
            },
            {
                "question": "How do I track my credit score?",
                "answer": "Your credit score is available through your bank or credit monitoring services. The app can show trends if integrated."
            },
            {
                "question": "What should I do if I think I have been charged fraudulently?",
                "answer": "If you suspect fraudulent activity, contact your bank immediately and review recent transactions."
            }
        ]
    })

@chatbot_bp.route('/api/chatbot/conversation-history', methods=['GET'])
def get_conversation_history_endpoint():
    """Get conversation history for a user"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        limit = int(request.args.get('limit', 20))
        conversations = list(conversations_collection.find(
            {'user_id': str(user_id)}
        ).sort('timestamp', -1).limit(limit))
        
        # Format conversations for frontend
        formatted_conversations = []
        for conv in reversed(conversations):  # Reverse to get chronological order
            formatted_conversations.append({
                'id': str(conv['_id']),
                'user_message': conv['user_message'],
                'bot_response': conv['bot_response'],
                'timestamp': conv['timestamp'].isoformat() if isinstance(conv['timestamp'], datetime) else conv['timestamp'],
                'date': conv['date']
            })
        
        return jsonify({
            'conversations': formatted_conversations,
            'total': len(formatted_conversations)
        })
    except Exception as e:
        print(f"Error getting conversation history: {e}")
        return jsonify({'error': 'Failed to get conversation history'}), 500

@chatbot_bp.route('/api/chatbot/clear-history', methods=['POST'])
def clear_conversation_history():
    """Clear conversation history for a user"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        if not user_id:
            return jsonify({'error': 'User ID is required'}), 400
        
        result = conversations_collection.delete_many({'user_id': str(user_id)})
        
        return jsonify({
            'message': f'Cleared {result.deleted_count} conversations',
            'deleted_count': result.deleted_count
        })
    except Exception as e:
        print(f"Error clearing conversation history: {e}")
        return jsonify({'error': 'Failed to clear conversation history'}), 500
