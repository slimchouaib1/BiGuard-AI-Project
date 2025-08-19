"""
Sample transaction data for BiGuard AI
Contains 2000+ transactions across all categories for testing and demonstration
"""

import random
from datetime import datetime, timedelta

# Transaction categories and their typical amounts
CATEGORIES = {
    'Food and Drink': {
        'restaurants': {'min': 15, 'max': 80, 'frequency': 0.12},
        'groceries': {'min': 30, 'max': 150, 'frequency': 0.10},
        'coffee shops': {'min': 3, 'max': 12, 'frequency': 0.08},
        'fast food': {'min': 8, 'max': 25, 'frequency': 0.08},
        'delivery': {'min': 20, 'max': 60, 'frequency': 0.06},
        'bakeries': {'min': 5, 'max': 20, 'frequency': 0.04},
        'food trucks': {'min': 8, 'max': 18, 'frequency': 0.03},
        'catering': {'min': 50, 'max': 200, 'frequency': 0.02},
        'alcohol': {'min': 15, 'max': 80, 'frequency': 0.05},
        'snacks': {'min': 2, 'max': 8, 'frequency': 0.06}
    },
    'Shopping': {
        'online shopping': {'min': 25, 'max': 200, 'frequency': 0.08},
        'clothing': {'min': 20, 'max': 120, 'frequency': 0.07},
        'electronics': {'min': 50, 'max': 500, 'frequency': 0.04},
        'home goods': {'min': 15, 'max': 100, 'frequency': 0.06},
        'jewelry': {'min': 50, 'max': 300, 'frequency': 0.02},
        'sports equipment': {'min': 30, 'max': 200, 'frequency': 0.03},
        'books': {'min': 10, 'max': 50, 'frequency': 0.04},
        'cosmetics': {'min': 15, 'max': 80, 'frequency': 0.05},
        'furniture': {'min': 100, 'max': 800, 'frequency': 0.02},
        'toys': {'min': 10, 'max': 60, 'frequency': 0.03},
        'pet supplies': {'min': 20, 'max': 100, 'frequency': 0.04},
        'office supplies': {'min': 10, 'max': 50, 'frequency': 0.03}
    },
    'Transportation': {
        'gas': {'min': 30, 'max': 80, 'frequency': 0.08},
        'uber': {'min': 12, 'max': 45, 'frequency': 0.06},
        'public transit': {'min': 2, 'max': 8, 'frequency': 0.05},
        'parking': {'min': 5, 'max': 25, 'frequency': 0.04},
        'car maintenance': {'min': 50, 'max': 300, 'frequency': 0.03},
        'car insurance': {'min': 80, 'max': 200, 'frequency': 0.02},
        'tolls': {'min': 2, 'max': 15, 'frequency': 0.04},
        'bike sharing': {'min': 2, 'max': 8, 'frequency': 0.03},
        'car wash': {'min': 10, 'max': 25, 'frequency': 0.03},
        'auto parts': {'min': 20, 'max': 150, 'frequency': 0.02}
    },
    'Entertainment': {
        'movies': {'min': 12, 'max': 35, 'frequency': 0.04},
        'concerts': {'min': 50, 'max': 200, 'frequency': 0.02},
        'bars': {'min': 20, 'max': 80, 'frequency': 0.06},
        'gym': {'min': 15, 'max': 50, 'frequency': 0.03},
        'sports events': {'min': 30, 'max': 150, 'frequency': 0.03},
        'museums': {'min': 10, 'max': 25, 'frequency': 0.02},
        'theme parks': {'min': 50, 'max': 150, 'frequency': 0.01},
        'bowling': {'min': 15, 'max': 40, 'frequency': 0.02},
        'arcade': {'min': 10, 'max': 30, 'frequency': 0.02},
        'karaoke': {'min': 20, 'max': 60, 'frequency': 0.02},
        'escape rooms': {'min': 25, 'max': 50, 'frequency': 0.01},
        'comedy clubs': {'min': 15, 'max': 40, 'frequency': 0.02}
    },
    'Bills and Utilities': {
        'electricity': {'min': 80, 'max': 200, 'frequency': 0.04},
        'internet': {'min': 50, 'max': 120, 'frequency': 0.04},
        'phone': {'min': 60, 'max': 150, 'frequency': 0.04},
        'rent': {'min': 800, 'max': 2500, 'frequency': 0.04},
        'water': {'min': 30, 'max': 80, 'frequency': 0.03},
        'gas': {'min': 40, 'max': 120, 'frequency': 0.03},
        'garbage': {'min': 20, 'max': 50, 'frequency': 0.02},
        'home insurance': {'min': 50, 'max': 150, 'frequency': 0.02},
        'property tax': {'min': 100, 'max': 500, 'frequency': 0.01},
        'hoa fees': {'min': 100, 'max': 300, 'frequency': 0.02}
    },
    'Healthcare': {
        'doctor': {'min': 25, 'max': 150, 'frequency': 0.03},
        'pharmacy': {'min': 15, 'max': 80, 'frequency': 0.05},
        'dental': {'min': 50, 'max': 300, 'frequency': 0.02},
        'vision': {'min': 30, 'max': 200, 'frequency': 0.02},
        'therapy': {'min': 80, 'max': 200, 'frequency': 0.02},
        'emergency room': {'min': 200, 'max': 1000, 'frequency': 0.01},
        'specialist': {'min': 100, 'max': 300, 'frequency': 0.02},
        'lab tests': {'min': 50, 'max': 200, 'frequency': 0.02},
        'medical equipment': {'min': 20, 'max': 150, 'frequency': 0.02},
        'health insurance': {'min': 200, 'max': 600, 'frequency': 0.02}
    },
    'Travel': {
        'hotels': {'min': 100, 'max': 400, 'frequency': 0.02},
        'airfare': {'min': 200, 'max': 800, 'frequency': 0.01},
        'rental car': {'min': 40, 'max': 150, 'frequency': 0.02},
        'vacation rentals': {'min': 150, 'max': 500, 'frequency': 0.01},
        'cruises': {'min': 500, 'max': 2000, 'frequency': 0.01},
        'tourist attractions': {'min': 20, 'max': 100, 'frequency': 0.02},
        'travel insurance': {'min': 30, 'max': 100, 'frequency': 0.01},
        'airport parking': {'min': 50, 'max': 200, 'frequency': 0.01},
        'travel gear': {'min': 30, 'max': 150, 'frequency': 0.02},
        'souvenirs': {'min': 10, 'max': 50, 'frequency': 0.02}
    },
    'Education': {
        'books': {'min': 20, 'max': 100, 'frequency': 0.03},
        'courses': {'min': 50, 'max': 300, 'frequency': 0.02},
        'software': {'min': 10, 'max': 50, 'frequency': 0.04},
        'tuition': {'min': 500, 'max': 3000, 'frequency': 0.01},
        'student loans': {'min': 200, 'max': 800, 'frequency': 0.02},
        'school supplies': {'min': 20, 'max': 100, 'frequency': 0.03},
        'certifications': {'min': 100, 'max': 500, 'frequency': 0.01},
        'workshops': {'min': 50, 'max': 200, 'frequency': 0.02},
        'conferences': {'min': 100, 'max': 500, 'frequency': 0.01},
        'online subscriptions': {'min': 10, 'max': 30, 'frequency': 0.04}
    },
    'Income': {
        'salary': {'min': 2000, 'max': 8000, 'frequency': 0.04},
        'freelance': {'min': 100, 'max': 500, 'frequency': 0.03},
        'bonus': {'min': 500, 'max': 2000, 'frequency': 0.01},
        'commission': {'min': 200, 'max': 1000, 'frequency': 0.02},
        'tips': {'min': 10, 'max': 100, 'frequency': 0.03},
        'investment returns': {'min': 50, 'max': 500, 'frequency': 0.02},
        'rental income': {'min': 500, 'max': 2000, 'frequency': 0.01},
        'refunds': {'min': 20, 'max': 200, 'frequency': 0.02},
        'gifts': {'min': 50, 'max': 300, 'frequency': 0.01}
    }
}

# Merchant names for each category
MERCHANTS = {
    'Food and Drink': {
        'restaurants': ['Chipotle', 'Panera Bread', 'Olive Garden', 'Red Lobster', 'Applebee\'s', 'TGI Fridays', 'Buffalo Wild Wings', 'Outback Steakhouse', 'Red Robin', 'Five Guys', 'Cheesecake Factory', 'P.F. Chang\'s', 'Bonefish Grill', 'Carrabba\'s', 'LongHorn Steakhouse', 'Texas Roadhouse', 'Cracker Barrel', 'IHOP', 'Denny\'s', 'Waffle House', 'Shake Shack', 'In-N-Out Burger', 'Whataburger', 'Culver\'s', 'Raising Cane\'s'],
        'groceries': ['Walmart', 'Target', 'Kroger', 'Safeway', 'Whole Foods', 'Trader Joe\'s', 'Publix', 'Albertsons', 'Food Lion', 'Giant Eagle', 'Meijer', 'H-E-B', 'Wegmans', 'ShopRite', 'Stop & Shop', 'Acme', 'Giant', 'Save A Lot', 'Aldi', 'Lidl', 'Sprouts', 'Fresh Market', 'Natural Grocers', 'Earth Fare'],
        'coffee shops': ['Starbucks', 'Dunkin\'', 'Peet\'s Coffee', 'Caribou Coffee', 'Tim Hortons', 'Dutch Bros', 'The Coffee Bean', 'Biggby Coffee', 'Gloria Jean\'s', 'Seattle\'s Best', 'Tully\'s Coffee', 'Coffee Beanery', 'Dunn Bros', 'The Human Bean', 'Black Rock Coffee Bar', 'Local Coffee Shop', 'Independent Cafe', 'Artisan Coffee'],
        'fast food': ['McDonald\'s', 'Burger King', 'Wendy\'s', 'Taco Bell', 'KFC', 'Subway', 'Domino\'s', 'Pizza Hut', 'Chick-fil-A', 'Popeyes', 'Arby\'s', 'Jack in the Box', 'Carl\'s Jr.', 'Hardee\'s', 'Sonic', 'Dairy Queen', 'Papa John\'s', 'Little Caesars', 'Papa Murphy\'s', 'Blaze Pizza', 'MOD Pizza', 'Pizza Ranch'],
        'delivery': ['DoorDash', 'Uber Eats', 'Grubhub', 'Postmates', 'Caviar', 'Seamless', 'Bite Squad', 'ChowNow', 'SkipTheDishes', 'Just Eat', 'Deliveroo', 'Foodpanda'],
        'bakeries': ['Panera Bread', 'Einstein Bros Bagels', 'Dunkin\'', 'Krispy Kreme', 'Cinnabon', 'Auntie Anne\'s', 'Mrs. Fields', 'Great American Cookies', 'Crumbl Cookies', 'Insomnia Cookies', 'Local Bakery', 'Artisan Bakery', 'French Bakery', 'German Bakery'],
        'food trucks': ['Taco Truck', 'Burger Truck', 'Pizza Truck', 'Ice Cream Truck', 'Coffee Truck', 'BBQ Truck', 'Asian Fusion Truck', 'Mediterranean Truck', 'Mexican Truck', 'Indian Truck'],
        'catering': ['Panera Bread', 'Olive Garden', 'Chipotle', 'Subway', 'Local Caterer', 'Professional Catering', 'Event Catering', 'Corporate Catering', 'Wedding Catering'],
        'alcohol': ['Total Wine', 'BevMo', 'ABC Liquor', 'Wine & Spirits', 'Liquor Store', 'Wine Shop', 'Craft Beer Store', 'Distillery', 'Brewery', 'Winery'],
        'snacks': ['7-Eleven', 'Circle K', 'Wawa', 'Sheetz', 'QuikTrip', 'Cumberland Farms', 'Speedway', 'Mobil', 'Shell', 'Exxon', 'Local Convenience Store']
    },
    'Shopping': {
        'online shopping': ['Amazon', 'eBay', 'Etsy', 'Walmart.com', 'Target.com', 'Best Buy', 'Newegg', 'Wayfair', 'Overstock', 'Chewy', 'Zappos', 'ASOS', 'Revolve', 'Shopify Store', 'BigCommerce', 'WooCommerce', 'Magento Store', 'Custom Online Store'],
        'clothing': ['Nike', 'Adidas', 'H&M', 'Zara', 'Uniqlo', 'Gap', 'Old Navy', 'Forever 21', 'Urban Outfitters', 'American Eagle', 'Aeropostale', 'Hollister', 'Abercrombie & Fitch', 'Express', 'Banana Republic', 'J.Crew', 'Macy\'s', 'Nordstrom', 'Bloomingdale\'s', 'Saks Fifth Avenue', 'Neiman Marcus', 'Bergdorf Goodman'],
        'electronics': ['Apple Store', 'Best Buy', 'Micro Center', 'B&H Photo', 'Adorama', 'Newegg', 'Amazon', 'Walmart', 'Target', 'Costco', 'Sam\'s Club', 'Fry\'s Electronics', 'TigerDirect', 'CDW', 'Insight', 'Connection', 'PC Connection'],
        'home goods': ['IKEA', 'Home Depot', 'Lowe\'s', 'Bed Bath & Beyond', 'Target', 'Walmart', 'Wayfair', 'Overstock', 'Pottery Barn', 'West Elm', 'Crate & Barrel', 'Williams-Sonoma', 'Sur La Table', 'Macy\'s', 'Kohl\'s', 'JCPenney', 'Sears', 'Kmart'],
        'jewelry': ['Kay Jewelers', 'Zales', 'Jared', 'Helzberg Diamonds', 'Pandora', 'Tiffany & Co.', 'Cartier', 'Rolex', 'Omega', 'Swatch', 'Fossil', 'Michael Kors', 'Kate Spade', 'Coach'],
        'sports equipment': ['Dick\'s Sporting Goods', 'Academy Sports', 'REI', 'Bass Pro Shops', 'Cabela\'s', 'Sports Authority', 'Modell\'s', 'Big 5 Sporting Goods', 'Dunham\'s Sports', 'Scheels'],
        'books': ['Barnes & Noble', 'Amazon', 'Bookstore', 'University Bookstore', 'Half Price Books', 'Powell\'s Books', 'Books-A-Million', 'Hastings', 'Borders', 'Waldenbooks', 'Local Bookstore', 'Independent Bookstore'],
        'cosmetics': ['Sephora', 'Ulta', 'MAC', 'Sally Beauty', 'Beauty Supply', 'CVS', 'Walgreens', 'Target', 'Walmart', 'Macy\'s', 'Nordstrom', 'Bloomingdale\'s', 'Saks Fifth Avenue'],
        'furniture': ['IKEA', 'Ashley Furniture', 'Rooms To Go', 'Bob\'s Discount Furniture', 'Value City Furniture', 'Raymour & Flanigan', 'Ethan Allen', 'Pottery Barn', 'West Elm', 'Crate & Barrel', 'Williams-Sonoma', 'Restoration Hardware'],
        'toys': ['Toys "R" Us', 'Target', 'Walmart', 'Amazon', 'GameStop', 'Best Buy', 'Barnes & Noble', 'Learning Express', 'Local Toy Store', 'Independent Toy Store'],
        'pet supplies': ['PetSmart', 'Petco', 'Pet Supplies Plus', 'Pet Valu', 'Pet Supermarket', 'Walmart', 'Target', 'Amazon', 'Chewy', 'PetFoodExpress'],
        'office supplies': ['Staples', 'Office Depot', 'OfficeMax', 'Amazon', 'Walmart', 'Target', 'Costco', 'Sam\'s Club', 'BJ\'s Wholesale', 'Local Office Supply']
    },
    'Transportation': {
        'gas': ['Shell', 'ExxonMobil', 'BP', 'Chevron', 'Texaco', 'Marathon', 'Sunoco', 'Valero', 'Phillips 66', 'Mobil', '76', 'Conoco', 'Hess', 'CITGO', 'Kum & Go', 'QuikTrip', 'Wawa', 'Sheetz', 'Speedway', 'Circle K'],
        'uber': ['Uber', 'Lyft', 'Uber Eats', 'Lyft Line', 'UberX', 'Uber Black', 'Uber Pool', 'Uber Comfort', 'UberXL', 'Uber Select', 'Lyft Plus', 'Lyft Premier'],
        'public transit': ['Metro', 'Bus System', 'Subway', 'Light Rail', 'Commuter Rail', 'Streetcar', 'Trolley', 'BART', 'Caltrain', 'Metrolink', 'Amtrak', 'Greyhound', 'Megabus', 'Local Transit Authority'],
        'parking': ['Parking Garage', 'Street Parking', 'Meter Parking', 'ParkMobile', 'SpotHero', 'ParkWhiz', 'ParkMe', 'BestParking', 'Parkopedia', 'Local Parking Authority'],
        'car maintenance': ['Jiffy Lube', 'Valvoline', 'Midas', 'Meineke', 'Firestone', 'Goodyear', 'Discount Tire', 'Les Schwab', 'NTB', 'Pep Boys', 'AutoZone', 'O\'Reilly Auto Parts', 'NAPA Auto Parts', 'Advance Auto Parts'],
        'car insurance': ['State Farm', 'Allstate', 'Geico', 'Progressive', 'Farmers', 'Liberty Mutual', 'Nationwide', 'American Family', 'Travelers', 'USAA', 'AAA', 'Esurance', 'MetLife'],
        'tolls': ['E-ZPass', 'FasTrak', 'TxTag', 'SunPass', 'Peach Pass', 'I-Pass', 'Illinois Tollway', 'New York Thruway', 'Pennsylvania Turnpike', 'Florida Turnpike'],
        'bike sharing': ['Citi Bike', 'Divvy', 'Capital Bikeshare', 'Bike Share', 'Lime', 'Bird', 'Spin', 'Jump', 'Lyft Bikes', 'Uber Bikes'],
        'car wash': ['Car Wash', 'Automatic Car Wash', 'Hand Car Wash', 'Detail Shop', 'Touchless Car Wash', 'Self-Service Car Wash', 'Full-Service Car Wash'],
        'auto parts': ['AutoZone', 'O\'Reilly Auto Parts', 'NAPA Auto Parts', 'Advance Auto Parts', 'Pep Boys', 'CarQuest', 'Bumper to Bumper', 'Parts Plus', 'Independent Auto Parts']
    },
    'Entertainment': {
        'movies': ['AMC Theatres', 'Regal Cinemas', 'Cinemark', 'Alamo Drafthouse', 'Landmark Theatres', 'Marcus Theatres', 'Harkins Theatres', 'Cineplex', 'Showcase Cinemas', 'ArcLight Cinemas', 'Arclight', 'Pacific Theatres', 'Edwards Theatres', 'Mann Theatres'],
        'concerts': ['Ticketmaster', 'Live Nation', 'AXS', 'Eventbrite', 'StubHub', 'Vivid Seats', 'SeatGeek', 'TicketCity', 'Tickets.com', 'Brown Paper Tickets', 'Local Concert Venue', 'Arena', 'Stadium', 'Amphitheater'],
        'bars': ['Local Bar', 'Sports Bar', 'Cocktail Lounge', 'Pub', 'Tavern', 'Brewery', 'Wine Bar', 'Nightclub', 'Dive Bar', 'Irish Pub', 'English Pub', 'Gastropub', 'Speakeasy', 'Rooftop Bar', 'Hotel Bar'],
        'gym': ['Planet Fitness', 'LA Fitness', '24 Hour Fitness', 'Gold\'s Gym', 'Anytime Fitness', 'Crunch Fitness', 'YMCA', 'Equinox', 'Lifetime Fitness', 'Orange Theory', 'CrossFit', 'Pure Barre', 'SoulCycle', 'Peloton', 'Local Gym'],
        'sports events': ['NFL Game', 'NBA Game', 'MLB Game', 'NHL Game', 'MLS Game', 'College Football', 'College Basketball', 'High School Sports', 'Local Sports Team', 'Minor League Sports'],
        'museums': ['Metropolitan Museum', 'Museum of Modern Art', 'Natural History Museum', 'Science Museum', 'Art Museum', 'History Museum', 'Children\'s Museum', 'Aquarium', 'Zoo', 'Botanical Garden', 'Local Museum'],
        'theme parks': ['Disney World', 'Disneyland', 'Universal Studios', 'Six Flags', 'Cedar Point', 'Busch Gardens', 'SeaWorld', 'Legoland', 'Hersheypark', 'Dollywood', 'Local Theme Park'],
        'bowling': ['AMF Bowling', 'Bowlmor', 'Bowlero', 'Lucky Strike', 'Local Bowling Alley', 'Family Bowling Center', 'Bowling Center'],
        'arcade': ['Dave & Buster\'s', 'Main Event', 'Round1', 'Chuck E. Cheese', 'Local Arcade', 'Gaming Center', 'Entertainment Center'],
        'karaoke': ['Karaoke Bar', 'Karaoke Lounge', 'Private Karaoke Room', 'Karaoke Night', 'Local Karaoke'],
        'escape rooms': ['Escape Room', 'Puzzle Room', 'Mystery Room', 'Adventure Room', 'Local Escape Room'],
        'comedy clubs': ['Comedy Club', 'Improv Theater', 'Stand-up Comedy', 'Comedy Cellar', 'Laugh Factory', 'Local Comedy Club']
    },
    'Bills and Utilities': {
        'electricity': ['Duke Energy', 'Pacific Gas & Electric', 'Southern California Edison', 'ConEdison', 'Florida Power & Light', 'American Electric Power', 'Dominion Energy', 'NextEra Energy', 'Exelon', 'FirstEnergy', 'PPL', 'Xcel Energy', 'Consumers Energy', 'DTE Energy'],
        'internet': ['Comcast', 'AT&T', 'Verizon', 'Spectrum', 'Cox Communications', 'Optimum', 'Frontier', 'CenturyLink', 'Mediacom', 'Windstream', 'HughesNet', 'Viasat', 'Starlink', 'Local Internet Provider'],
        'phone': ['Verizon', 'AT&T', 'T-Mobile', 'Sprint', 'Cricket Wireless', 'Metro by T-Mobile', 'Boost Mobile', 'Virgin Mobile', 'Mint Mobile', 'Google Fi', 'Visible', 'US Cellular', 'Consumer Cellular'],
        'rent': ['Property Management', 'Landlord', 'Apartment Complex', 'Rental Agency', 'Real Estate Company', 'Property Owner', 'Housing Authority', 'Student Housing', 'Corporate Housing'],
        'water': ['City Water Department', 'County Water Authority', 'Municipal Water', 'Water Utility', 'Local Water Company', 'Water District'],
        'gas': ['Pacific Gas & Electric', 'Southern California Gas', 'ConEdison', 'National Grid', 'Dominion Energy', 'CenterPoint Energy', 'Atmos Energy', 'Southwest Gas', 'Local Gas Company'],
        'garbage': ['Waste Management', 'Republic Services', 'Waste Connections', 'Advanced Disposal', 'Local Garbage Service', 'City Sanitation', 'County Waste', 'Private Waste Company'],
        'home insurance': ['State Farm', 'Allstate', 'Geico', 'Progressive', 'Farmers', 'Liberty Mutual', 'Nationwide', 'American Family', 'Travelers', 'USAA', 'AAA', 'Esurance', 'MetLife'],
        'property tax': ['County Tax Assessor', 'City Tax Office', 'Property Tax Authority', 'Local Government', 'Tax Collector', 'County Treasurer'],
        'hoa fees': ['Homeowners Association', 'HOA Management', 'Property Management', 'Community Association', 'Neighborhood Association']
    },
    'Healthcare': {
        'doctor': ['Primary Care Physician', 'Specialist', 'Urgent Care', 'Medical Center', 'Clinic', 'Hospital', 'Dermatologist', 'Cardiologist', 'Orthopedist', 'Neurologist', 'Psychiatrist', 'Psychologist', 'Pediatrician', 'Obstetrician', 'Gynecologist', 'Oncologist', 'Endocrinologist', 'Gastroenterologist'],
        'pharmacy': ['CVS Pharmacy', 'Walgreens', 'Rite Aid', 'Walmart Pharmacy', 'Target Pharmacy', 'Kroger Pharmacy', 'Safeway Pharmacy', 'Albertsons Pharmacy', 'Publix Pharmacy', 'Meijer Pharmacy', 'H-E-B Pharmacy', 'Wegmans Pharmacy', 'Independent Pharmacy', 'Local Pharmacy'],
        'dental': ['Dental Office', 'Dentist', 'Orthodontist', 'Dental Clinic', 'Smile Center', 'Family Dentistry', 'Cosmetic Dentistry', 'Pediatric Dentistry', 'Oral Surgeon', 'Endodontist', 'Periodontist', 'Dental Specialist'],
        'vision': ['LensCrafters', 'Pearle Vision', 'Visionworks', 'America\'s Best', 'Walmart Vision Center', 'Target Optical', 'Costco Optical', 'Independent Optometrist', 'Eye Doctor', 'Vision Clinic', 'Optical Shop'],
        'therapy': ['Therapy Office', 'Counseling Center', 'Mental Health Clinic', 'Psychologist', 'Psychiatrist', 'Therapist', 'Counselor', 'Social Worker', 'Marriage Counselor', 'Family Therapist', 'Group Therapy'],
        'emergency room': ['Emergency Room', 'ER', 'Emergency Department', 'Trauma Center', 'Urgent Care', 'Emergency Medical Center', 'Hospital Emergency'],
        'specialist': ['Medical Specialist', 'Specialist Doctor', 'Specialist Office', 'Specialist Clinic', 'Medical Specialist Center'],
        'lab tests': ['LabCorp', 'Quest Diagnostics', 'Lab Test', 'Medical Laboratory', 'Diagnostic Lab', 'Blood Test Lab', 'Urine Test Lab', 'Pathology Lab'],
        'medical equipment': ['Medical Supply Store', 'Durable Medical Equipment', 'Home Medical Equipment', 'Medical Device Store', 'Healthcare Supply', 'Medical Equipment Rental'],
        'health insurance': ['Blue Cross Blue Shield', 'Aetna', 'Cigna', 'UnitedHealth Group', 'Humana', 'Kaiser Permanente', 'Anthem', 'Health Net', 'Molina Healthcare', 'Centene', 'WellCare', 'Local Health Insurance']
    },
    'Travel': {
        'hotels': ['Marriott', 'Hilton', 'Hyatt', 'InterContinental', 'Sheraton', 'Holiday Inn', 'Best Western', 'Comfort Inn', 'Days Inn', 'Motel 6', 'Super 8', 'Quality Inn', 'Ramada', 'Wyndham', 'Choice Hotels', 'La Quinta', 'Red Roof Inn', 'Extended Stay America', 'Residence Inn', 'Courtyard by Marriott'],
        'airfare': ['Delta Airlines', 'American Airlines', 'United Airlines', 'Southwest Airlines', 'JetBlue', 'Alaska Airlines', 'Spirit Airlines', 'Frontier Airlines', 'Allegiant Air', 'Hawaiian Airlines', 'Air Canada', 'WestJet', 'British Airways', 'Lufthansa', 'Air France'],
        'rental car': ['Hertz', 'Enterprise', 'Avis', 'Budget', 'National', 'Alamo', 'Thrifty', 'Dollar', 'Sixt', 'Payless', 'Advantage', 'Fox Rent A Car', 'ACE Rent A Car', 'Local Car Rental'],
        'vacation rentals': ['Airbnb', 'VRBO', 'HomeAway', 'Vacation Rental', 'Vacation Home', 'Beach House', 'Mountain Cabin', 'City Apartment', 'Country House', 'Luxury Rental'],
        'cruises': ['Royal Caribbean', 'Carnival Cruise Line', 'Norwegian Cruise Line', 'Disney Cruise Line', 'Princess Cruises', 'Holland America', 'Celebrity Cruises', 'MSC Cruises', 'Costa Cruises', 'Cunard Line'],
        'tourist attractions': ['Tourist Attraction', 'Theme Park', 'Museum', 'Zoo', 'Aquarium', 'Botanical Garden', 'Historical Site', 'National Park', 'State Park', 'Local Attraction'],
        'travel insurance': ['Travel Insurance', 'Trip Insurance', 'Travel Protection', 'Travel Guard', 'Allianz Travel', 'World Nomads', 'InsureMyTrip', 'Squaremouth', 'Travel Insurance Center'],
        'airport parking': ['Airport Parking', 'Long-term Parking', 'Short-term Parking', 'Economy Parking', 'Premium Parking', 'Valet Parking', 'Off-site Parking', 'Park and Fly'],
        'travel gear': ['Travel Store', 'Luggage Store', 'Travel Accessories', 'Outdoor Store', 'Camping Store', 'Hiking Store', 'Travel Gear Shop'],
        'souvenirs': ['Souvenir Shop', 'Gift Shop', 'Tourist Shop', 'Local Market', 'Craft Market', 'Artisan Shop', 'Local Store']
    },
    'Education': {
        'books': ['Barnes & Noble', 'Amazon', 'Bookstore', 'University Bookstore', 'Half Price Books', 'Powell\'s Books', 'Books-A-Million', 'Hastings', 'Borders', 'Waldenbooks', 'Local Bookstore', 'Independent Bookstore', 'Textbook Store', 'Online Bookstore'],
        'courses': ['Coursera', 'Udemy', 'edX', 'Skillshare', 'MasterClass', 'LinkedIn Learning', 'Pluralsight', 'Treehouse', 'Codecademy', 'DataCamp', 'Khan Academy', 'MIT OpenCourseWare', 'Stanford Online', 'Harvard Online'],
        'software': ['Adobe', 'Microsoft', 'Autodesk', 'JetBrains', 'Sketch', 'Figma', 'Notion', 'Slack', 'Zoom', 'Dropbox', 'Google Workspace', 'Apple', 'Oracle', 'SAP', 'Salesforce', 'HubSpot', 'Mailchimp', 'Canva'],
        'tuition': ['University', 'College', 'Community College', 'Technical School', 'Trade School', 'Vocational School', 'Online University', 'Distance Learning', 'Continuing Education'],
        'student loans': ['Federal Student Loans', 'Private Student Loans', 'Sallie Mae', 'Navient', 'Great Lakes', 'Nelnet', 'FedLoan Servicing', 'MOHELA', 'AES', 'Cornerstone'],
        'school supplies': ['Staples', 'Office Depot', 'OfficeMax', 'Target', 'Walmart', 'Amazon', 'Local School Supply Store', 'University Bookstore', 'School Supply Store'],
        'certifications': ['Certification Program', 'Professional Certification', 'Industry Certification', 'Technical Certification', 'Online Certification', 'Certification Course'],
        'workshops': ['Workshop', 'Training Workshop', 'Professional Workshop', 'Skill Workshop', 'Educational Workshop', 'Local Workshop'],
        'conferences': ['Conference', 'Professional Conference', 'Industry Conference', 'Academic Conference', 'Tech Conference', 'Business Conference'],
        'online subscriptions': ['Netflix', 'Hulu', 'Disney+', 'Amazon Prime', 'Apple TV+', 'HBO Max', 'Peacock', 'Paramount+', 'Discovery+', 'YouTube Premium', 'Spotify', 'Apple Music', 'Amazon Music', 'Pandora']
    },
    'Income': {
        'salary': ['Employer', 'Company', 'Corporation', 'Inc.', 'LLC', 'Partnership', 'Organization', 'Business', 'Enterprise', 'Firm', 'Agency', 'Department', 'Division', 'Branch', 'Office'],
        'freelance': ['Client', 'Freelance Project', 'Contract Work', 'Consulting', 'Gig Work', 'Side Project', 'Independent Contractor', 'Freelance Client', 'Project Payment', 'Contract Payment'],
        'bonus': ['Employer', 'Company', 'Corporation', 'Inc.', 'LLC', 'Partnership', 'Organization', 'Business', 'Enterprise', 'Firm', 'Agency', 'Department', 'Division', 'Branch', 'Office'],
        'commission': ['Commission Payment', 'Sales Commission', 'Real Estate Commission', 'Insurance Commission', 'Financial Commission', 'Trading Commission'],
        'tips': ['Tip Payment', 'Service Tip', 'Restaurant Tip', 'Delivery Tip', 'Service Industry Tip', 'Gratuity'],
        'investment returns': ['Investment Return', 'Dividend Payment', 'Interest Payment', 'Capital Gains', 'Investment Income', 'Portfolio Return', 'Stock Dividend', 'Bond Interest'],
        'rental income': ['Rental Income', 'Property Rental', 'Real Estate Rental', 'Apartment Rental', 'House Rental', 'Commercial Rental', 'Investment Property'],
        'refunds': ['Refund', 'Purchase Refund', 'Return Refund', 'Tax Refund', 'Insurance Refund', 'Overpayment Refund', 'Credit Refund'],
        'gifts': ['Gift', 'Monetary Gift', 'Cash Gift', 'Birthday Gift', 'Holiday Gift', 'Wedding Gift', 'Graduation Gift', 'Anniversary Gift']
    }
}

def generate_sample_transactions(count=2000, user_id=None, account_id=None):
    """
    Generate sample transactions for testing
    Returns a list of transaction dictionaries
    """
    transactions = []
    
    # Generate transactions over the last 6 months
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    for i in range(count):
        # Random date within the range
        random_days = random.randint(0, 180)
        transaction_date = end_date - timedelta(days=random_days)
        
        # Select random category and subcategory
        category = random.choice(list(CATEGORIES.keys()))
        subcategory = random.choice(list(CATEGORIES[category].keys()))
        
        # Get amount range and frequency
        amount_info = CATEGORIES[category][subcategory]
        
        # Generate amount
        amount = round(random.uniform(amount_info['min'], amount_info['max']), 2)
        
        # For income categories, make amount positive; for others, make it negative (spending)
        if category == 'Income':
            amount = abs(amount)
        else:
            amount = -abs(amount)
        
        # Select merchant
        merchant_list = MERCHANTS[category][subcategory]
        merchant = random.choice(merchant_list)
        
        # Generate transaction name
        if category == 'Income':
            if subcategory == 'salary':
                transaction_name = f"Salary - {merchant}"
            elif subcategory == 'freelance':
                transaction_name = f"Freelance Payment - {merchant}"
            else:
                transaction_name = f"Bonus - {merchant}"
        else:
            transaction_name = f"{merchant} - {subcategory.replace('_', ' ').title()}"
        
        # Create transaction object
        transaction = {
            'user_id': user_id,
            'account_id': account_id,
            'name': transaction_name,
            'amount': amount,
            'category': category,
            'subcategory': subcategory,
            'merchant_name': merchant,
            'date': transaction_date.strftime('%Y-%m-%d'),
            'transaction_type': 'income' if category == 'Income' else 'spending',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        transactions.append(transaction)
    
    return transactions

def get_sample_transactions_for_button(count=2000):
    """
    Get sample transactions for the generate button (without user/account IDs)
    These will be assigned when actually creating the transactions
    """
    return generate_sample_transactions(count)

if __name__ == "__main__":
    # Test generation
    sample_txs = generate_sample_transactions(10)
    for tx in sample_txs:
        print(f"{tx['date']}: {tx['name']} - {tx['amount']} ({tx['category']})")
