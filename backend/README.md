# BiGuard Backend

A Flask-based backend for the BiGuard personal finance assistant with real-time bank transaction monitoring and fraud detection using Plaid API and Azure SQL Database.

## Features

- **User Authentication**: JWT-based authentication with bcrypt password hashing
- **Plaid Integration**: Real-time bank account connection and transaction syncing
- **Fraud Detection**: Machine learning-based anomaly detection using scikit-learn
- **Transaction Management**: CRUD operations for transactions with filtering and pagination
- **Budget Management**: Create and track budgets by category
- **Dashboard Analytics**: Real-time financial statistics and fraud alerts
- **Azure SQL Database**: Scalable cloud database integration

## Prerequisites

- Python 3.8+
- Plaid API account (Sandbox for development)
- Azure SQL Database (optional for production)
- Redis (for background tasks)

## Installation

1. **Clone the repository and navigate to backend directory**
   ```bash
   cd backend
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your actual values
   ```

5. **Get Plaid API credentials**
   - Sign up at [Plaid Dashboard](https://dashboard.plaid.com/)
   - Get your Client ID and Secret from the Sandbox environment
   - Update your `.env` file with these credentials

## Configuration

### Environment Variables

Create a `.env` file in the backend directory with the following variables:

```env
# Flask Configuration
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here

# Database Configuration
DATABASE_URL=sqlite:///biguard.db  # For development
# DATABASE_URL=mssql+pyodbc://username:password@server.database.windows.net:1433/database?driver=ODBC+Driver+17+for+SQL+Server  # For production

# Plaid Configuration
PLAID_CLIENT_ID=your-plaid-client-id
PLAID_SECRET=your-plaid-secret-key

# Optional: Azure Configuration (for production)
AZURE_TENANT_ID=your-azure-tenant-id
AZURE_CLIENT_ID=your-azure-client-id
AZURE_CLIENT_SECRET=your-azure-client-secret

# Optional: SendGrid Configuration
SENDGRID_API_KEY=your-sendgrid-api-key
SENDGRID_FROM_EMAIL=noreply@biguard.com

# Optional: Firebase Configuration
FIREBASE_CREDENTIALS_PATH=path/to/firebase-credentials.json

# Optional: Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Application Configuration
DEBUG=True
FLASK_ENV=development
```

### Plaid Sandbox Setup

1. **Get API Credentials**
   - Go to [Plaid Dashboard](https://dashboard.plaid.com/)
   - Create a new app in Sandbox environment
   - Copy your Client ID and Secret

2. **Test Credentials**
   - The app uses Plaid's Sandbox environment for development
   - Sandbox provides fake bank data for testing
   - No real bank connections needed for development

## Database Setup

### Local Development (SQLite)
The app will automatically create a SQLite database when you first run it.

### Azure SQL Database (Production)
1. Create an Azure SQL Database
2. Install ODBC Driver 17 for SQL Server
3. Update `DATABASE_URL` in your `.env` file
4. Run database migrations

## Running the Application

1. **Start the Flask server**
   ```bash
   python app.py
   ```

2. **The API will be available at**
   ```
   http://localhost:5000
   ```

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register a new user
- `POST /api/auth/login` - Login user

### Plaid Integration
- `POST /api/plaid/create-link-token` - Create Plaid Link token
- `POST /api/plaid/exchange-token` - Exchange public token for access token

### Transactions
- `POST /api/transactions/sync` - Sync transactions from Plaid
- `GET /api/transactions` - Get user transactions (with filtering)

### Dashboard
- `GET /api/dashboard/stats` - Get dashboard statistics

### Budgets
- `GET /api/budgets` - Get user budgets
- `POST /api/budgets` - Create new budget

## Machine Learning - Fraud Detection

The application includes a machine learning-based fraud detection system:

### Features Used
- Transaction amount ratio to user's average
- Frequency of recent transactions
- New merchant detection
- Category frequency analysis
- Transaction amount normalization

### Algorithm
- **Isolation Forest**: Anomaly detection algorithm
- **Threshold**: 0.7 (transactions above this score are flagged as fraudulent)
- **Training**: Uses user's transaction history for personalized detection

### How it Works
1. When a new transaction is synced, the system calculates a fraud score
2. Features are extracted from the transaction and user's history
3. An Isolation Forest model is trained on the user's transaction patterns
4. The new transaction is scored based on how anomalous it appears
5. Transactions with scores > 0.7 are flagged as potentially fraudulent

## Development

### Project Structure
```
backend/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── env.example         # Environment variables template
├── README.md          # This file
└── biguard.db         # SQLite database (created automatically)
```

### Adding New Features
1. Add new models to the database models section
2. Create new API endpoints
3. Update the database schema if needed
4. Test with the frontend

### Testing
```bash
# Run the application in debug mode
python app.py
```

## Production Deployment

### Azure Deployment
1. Set up Azure App Service
2. Configure environment variables
3. Set up Azure SQL Database
4. Deploy using Azure CLI or GitHub Actions

### Environment Variables for Production
- Set `DEBUG=False`
- Use strong secret keys
- Configure Azure SQL Database connection
- Set up SendGrid for email notifications
- Configure Firebase for push notifications

## Security Considerations

- All passwords are hashed using bcrypt
- JWT tokens for authentication
- CORS enabled for frontend integration
- Environment variables for sensitive data
- HTTPS required in production

## Troubleshooting

### Common Issues

1. **Plaid API Errors**
   - Verify your Plaid credentials
   - Check if you're using Sandbox environment
   - Ensure your app is properly configured in Plaid Dashboard

2. **Database Connection Issues**
   - Verify your database URL
   - Check if the database server is running
   - Ensure proper permissions

3. **Import Errors**
   - Make sure all dependencies are installed
   - Check Python version compatibility
   - Verify virtual environment is activated

### Getting Help
- Check the Plaid documentation: https://plaid.com/docs/
- Review Flask documentation: https://flask.palletsprojects.com/
- Check Azure SQL documentation: https://docs.microsoft.com/en-us/azure/azure-sql/

## License

This project is part of the BiGuard personal finance assistant application. 