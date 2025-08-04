from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import uuid
from datetime import datetime, timedelta
import math

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Models
class Bond(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    country: str
    country_code: str
    face_value: float
    coupon_rate: float  # Annual coupon rate
    maturity_date: str
    issue_date: str
    current_price: float
    risk_factor: float  # Country risk in percentage
    currency: str = "USD"
    total_supply: int
    available_supply: int

class Portfolio(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_address: str
    bonds: Dict[str, float] = {}  # bond_id -> quantity owned
    total_value: float = 0.0
    total_yield: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)

class BondTransaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_address: str
    bond_id: str
    transaction_type: str  # "buy" or "sell"
    quantity: float
    price_per_bond: float
    total_amount: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class TradeRequest(BaseModel):
    user_address: str
    bond_id: str
    quantity: float
    transaction_type: str  # "buy" or "sell"

# Mock bond data with realistic parameters
MOCK_BONDS = [
    {
        "country": "Ghana",
        "country_code": "GH",
        "face_value": 1000.0,
        "coupon_rate": 7.5,
        "maturity_date": "2029-12-31",
        "issue_date": "2024-01-01",
        "current_price": 950.0,
        "risk_factor": 2.3,
        "currency": "USD",
        "total_supply": 10000,
        "available_supply": 7500
    },
    {
        "country": "Nigeria",
        "country_code": "NG", 
        "face_value": 1000.0,
        "coupon_rate": 8.2,
        "maturity_date": "2026-06-30",
        "issue_date": "2023-07-01",
        "current_price": 920.0,
        "risk_factor": 4.1,
        "currency": "USD",
        "total_supply": 15000,
        "available_supply": 12000
    },
    {
        "country": "Kenya",
        "country_code": "KE",
        "face_value": 1000.0,
        "coupon_rate": 6.8,
        "maturity_date": "2028-03-15",
        "issue_date": "2023-03-15",
        "current_price": 965.0,
        "risk_factor": 1.8,
        "currency": "USD",
        "total_supply": 8000,
        "available_supply": 5500
    },
    {
        "country": "South Africa",
        "country_code": "ZA",
        "face_value": 1000.0,
        "coupon_rate": 9.1,
        "maturity_date": "2027-09-30",
        "issue_date": "2023-10-01",
        "current_price": 890.0,
        "risk_factor": 5.2,
        "currency": "USD",
        "total_supply": 20000,
        "available_supply": 18500
    }
]

# Risk Engine Functions
def calculate_dynamic_yield(bond: Bond) -> float:
    """Calculate dynamic yield based on risk factors"""
    base_yield = bond.coupon_rate
    risk_adjusted_yield = base_yield * (1 + bond.risk_factor / 100)
    
    # Add time-to-maturity factor
    maturity_date = datetime.strptime(bond.maturity_date, "%Y-%m-%d")
    years_to_maturity = (maturity_date - datetime.now()).days / 365.25
    
    # Longer maturity = higher yield
    maturity_adjustment = max(0, years_to_maturity - 2) * 0.3
    
    return round(risk_adjusted_yield + maturity_adjustment, 2)

def calculate_bond_price(bond: Bond, market_demand: float = 1.0) -> float:
    """AMM-style pricing with supply/demand dynamics"""
    base_price = bond.current_price
    
    # Supply scarcity factor
    scarcity_factor = 1 - (bond.available_supply / bond.total_supply)
    scarcity_adjustment = scarcity_factor * 50  # Max 50 USD premium for scarcity
    
    # Risk adjustment
    risk_discount = bond.risk_factor * 10  # Higher risk = lower price
    
    # Market demand (simulated)
    demand_adjustment = (market_demand - 1) * 25
    
    final_price = base_price + scarcity_adjustment - risk_discount + demand_adjustment
    return max(final_price, bond.face_value * 0.7)  # Minimum 70% of face value

async def initialize_bonds():
    """Initialize mock bonds in database"""
    existing_bonds = await db.bonds.count_documents({})
    if existing_bonds == 0:
        for bond_data in MOCK_BONDS:
            bond = Bond(**bond_data)
            bond.id = str(uuid.uuid4())
            await db.bonds.insert_one(bond.dict())

# API Routes
@api_router.get("/")
async def root():
    return {"message": "Sovereign Bond Marketplace API"}

@api_router.get("/bonds", response_model=List[Bond])
async def get_bonds():
    """Get all available bonds with dynamic pricing"""
    await initialize_bonds()
    bonds = await db.bonds.find().to_list(1000)
    
    # Update prices dynamically
    for bond_data in bonds:
        bond = Bond(**bond_data)
        # Simulate market demand fluctuation
        import random
        market_demand = random.uniform(0.8, 1.3)
        updated_price = calculate_bond_price(bond, market_demand)
        bond.current_price = round(updated_price, 2)
        
        # Update in database
        await db.bonds.update_one(
            {"id": bond.id},
            {"$set": {"current_price": bond.current_price}}
        )
    
    # Re-fetch updated bonds
    updated_bonds = await db.bonds.find().to_list(1000)
    return [Bond(**bond) for bond in updated_bonds]

@api_router.get("/bonds/{bond_id}", response_model=Bond)
async def get_bond(bond_id: str):
    """Get specific bond details"""
    bond_data = await db.bonds.find_one({"id": bond_id})
    if not bond_data:
        raise HTTPException(status_code=404, detail="Bond not found")
    return Bond(**bond_data)

@api_router.get("/bonds/{bond_id}/yield")
async def get_bond_yield(bond_id: str):
    """Get dynamic yield for a specific bond"""
    bond_data = await db.bonds.find_one({"id": bond_id})
    if not bond_data:
        raise HTTPException(status_code=404, detail="Bond not found")
    
    bond = Bond(**bond_data)
    dynamic_yield = calculate_dynamic_yield(bond)
    
    return {
        "bond_id": bond_id,
        "country": bond.country,
        "base_yield": bond.coupon_rate,
        "risk_factor": bond.risk_factor,
        "dynamic_yield": dynamic_yield,
        "current_price": bond.current_price,
        "face_value": bond.face_value
    }

@api_router.post("/trade")
async def execute_trade(trade: TradeRequest):
    """Execute bond trade through AMM"""
    # Get bond
    bond_data = await db.bonds.find_one({"id": trade.bond_id})
    if not bond_data:
        raise HTTPException(status_code=404, detail="Bond not found")
    
    bond = Bond(**bond_data)
    
    # Check availability for buy orders
    if trade.transaction_type == "buy" and trade.quantity > bond.available_supply:
        raise HTTPException(status_code=400, detail="Insufficient bond supply")
    
    # Calculate trade price
    trade_price = calculate_bond_price(bond)
    total_amount = trade_price * trade.quantity
    
    # Create transaction record
    transaction = BondTransaction(
        user_address=trade.user_address,
        bond_id=trade.bond_id,
        transaction_type=trade.transaction_type,
        quantity=trade.quantity,
        price_per_bond=trade_price,
        total_amount=total_amount
    )
    
    await db.transactions.insert_one(transaction.dict())
    
    # Update bond supply
    if trade.transaction_type == "buy":
        new_available_supply = bond.available_supply - trade.quantity
    else:
        new_available_supply = bond.available_supply + trade.quantity
    
    await db.bonds.update_one(
        {"id": trade.bond_id},
        {"$set": {"available_supply": new_available_supply}}
    )
    
    # Update or create user portfolio
    portfolio_data = await db.portfolios.find_one({"user_address": trade.user_address})
    
    if portfolio_data:
        portfolio = Portfolio(**portfolio_data)
    else:
        portfolio = Portfolio(user_address=trade.user_address)
    
    # Update portfolio holdings
    if trade.bond_id not in portfolio.bonds:
        portfolio.bonds[trade.bond_id] = 0
    
    if trade.transaction_type == "buy":
        portfolio.bonds[trade.bond_id] += trade.quantity
    else:
        portfolio.bonds[trade.bond_id] -= trade.quantity
        if portfolio.bonds[trade.bond_id] <= 0:
            del portfolio.bonds[trade.bond_id]
    
    # Recalculate portfolio value
    total_value = 0
    total_yield = 0
    
    for bond_id, quantity in portfolio.bonds.items():
        bond_info = await db.bonds.find_one({"id": bond_id})
        if bond_info:
            bond_obj = Bond(**bond_info)
            total_value += bond_obj.current_price * quantity
            bond_yield = calculate_dynamic_yield(bond_obj)
            total_yield += bond_yield * (bond_obj.current_price * quantity) / total_value if total_value > 0 else 0
    
    portfolio.total_value = round(total_value, 2)
    portfolio.total_yield = round(total_yield, 2)
    
    # Save portfolio
    await db.portfolios.replace_one(
        {"user_address": trade.user_address},
        portfolio.dict(),
        upsert=True
    )
    
    return {
        "success": True,
        "transaction_id": transaction.id,
        "trade_price": trade_price,
        "total_amount": total_amount,
        "new_portfolio_value": portfolio.total_value
    }

@api_router.get("/portfolio/{user_address}")
async def get_portfolio(user_address: str):
    """Get user portfolio with detailed bond information"""
    portfolio_data = await db.portfolios.find_one({"user_address": user_address})
    
    if not portfolio_data:
        return Portfolio(user_address=user_address)
    
    portfolio = Portfolio(**portfolio_data)
    
    # Enrich with bond details
    detailed_holdings = []
    for bond_id, quantity in portfolio.bonds.items():
        bond_data = await db.bonds.find_one({"id": bond_id})
        if bond_data:
            bond = Bond(**bond_data)
            yield_info = calculate_dynamic_yield(bond)
            holding_value = bond.current_price * quantity
            
            detailed_holdings.append({
                "bond": bond.dict(),
                "quantity": quantity,
                "current_value": round(holding_value, 2),
                "dynamic_yield": yield_info,
                "unrealized_pnl": round((bond.current_price - bond.face_value) * quantity, 2)
            })
    
    return {
        "portfolio": portfolio.dict(),
        "detailed_holdings": detailed_holdings,
        "summary": {
            "total_bonds": len(portfolio.bonds),
            "total_value": portfolio.total_value,
            "average_yield": portfolio.total_yield
        }
    }

@api_router.get("/market-stats")
async def get_market_stats():
    """Get overall market statistics"""
    bonds = await db.bonds.find().to_list(1000)
    transactions = await db.transactions.find().to_list(1000)
    
    total_market_value = sum(bond["current_price"] * bond["total_supply"] for bond in bonds)
    total_volume_24h = sum(tx["total_amount"] for tx in transactions if 
                          datetime.now() - tx["timestamp"] < timedelta(days=1))
    
    avg_yield = sum(calculate_dynamic_yield(Bond(**bond)) for bond in bonds) / len(bonds) if bonds else 0
    
    return {
        "total_market_value": round(total_market_value, 2),
        "total_volume_24h": round(total_volume_24h, 2),
        "average_yield": round(avg_yield, 2),
        "active_bonds": len(bonds),
        "total_transactions": len(transactions)
    }

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()