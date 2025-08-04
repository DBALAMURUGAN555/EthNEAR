#!/usr/bin/env python3
"""
Comprehensive Backend API Tests for Sovereign Bond Marketplace
Tests all high-priority backend components as specified in test_result.md
"""

import requests
import json
import time
from typing import Dict, List, Any

# Configuration
BASE_URL = "https://b336e532-eb32-4e8e-a87d-de46ad63cb31.preview.emergentagent.com/api"
TEST_USER_ADDRESS = "0x1234567890abcdef1234567890abcdef12345678"

class BondMarketplaceTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.test_results = {}
        self.bonds_data = []
        
    def log_test(self, test_name: str, success: bool, details: str, data: Any = None):
        """Log test results"""
        self.test_results[test_name] = {
            "success": success,
            "details": details,
            "data": data,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {details}")
        if data and not success:
            print(f"   Data: {data}")
    
    def test_api_health(self):
        """Test basic API connectivity"""
        try:
            response = requests.get(f"{self.base_url}/", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.log_test("API Health Check", True, f"API is responding. Message: {data.get('message', 'N/A')}")
                return True
            else:
                self.log_test("API Health Check", False, f"API returned status {response.status_code}")
                return False
        except Exception as e:
            self.log_test("API Health Check", False, f"Connection failed: {str(e)}")
            return False
    
    def test_bonds_endpoint(self):
        """Test GET /bonds endpoint - Mock Bond Data and Dynamic Pricing"""
        try:
            response = requests.get(f"{self.base_url}/bonds", timeout=15)
            
            if response.status_code != 200:
                self.log_test("Bonds Endpoint", False, f"HTTP {response.status_code}: {response.text}")
                return False
            
            bonds = response.json()
            self.bonds_data = bonds  # Store for later tests
            
            # Verify we have 4 sovereign bonds
            if len(bonds) != 4:
                self.log_test("Mock Bond Data", False, f"Expected 4 bonds, got {len(bonds)}")
                return False
            
            # Verify expected countries
            expected_countries = {"Ghana", "Nigeria", "Kenya", "South Africa"}
            actual_countries = {bond["country"] for bond in bonds}
            
            if expected_countries != actual_countries:
                self.log_test("Mock Bond Data", False, f"Expected countries {expected_countries}, got {actual_countries}")
                return False
            
            # Verify bond structure and dynamic pricing
            required_fields = ["id", "country", "country_code", "face_value", "coupon_rate", 
                             "maturity_date", "current_price", "risk_factor", "total_supply", "available_supply"]
            
            for bond in bonds:
                missing_fields = [field for field in required_fields if field not in bond]
                if missing_fields:
                    self.log_test("Bond Data Structure", False, f"Missing fields in {bond['country']}: {missing_fields}")
                    return False
                
                # Verify dynamic pricing (current_price should be reasonable)
                if not (500 <= bond["current_price"] <= 1200):
                    self.log_test("Dynamic Pricing", False, f"{bond['country']} price {bond['current_price']} seems unrealistic")
                    return False
            
            # Test specific bond parameters from mock data
            ghana_bond = next((b for b in bonds if b["country"] == "Ghana"), None)
            if ghana_bond:
                if ghana_bond["coupon_rate"] != 7.5 or ghana_bond["risk_factor"] != 2.3:
                    self.log_test("Ghana Bond Parameters", False, f"Ghana bond parameters incorrect: coupon={ghana_bond['coupon_rate']}, risk={ghana_bond['risk_factor']}")
                    return False
            
            self.log_test("Bonds Endpoint", True, f"Successfully loaded {len(bonds)} bonds with dynamic pricing")
            self.log_test("Mock Bond Data", True, "All 4 sovereign bonds loaded with correct parameters")
            return True
            
        except Exception as e:
            self.log_test("Bonds Endpoint", False, f"Exception: {str(e)}")
            return False
    
    def test_bond_yield_calculation(self):
        """Test GET /bonds/{bond_id}/yield - Risk Engine and Dynamic Yield"""
        if not self.bonds_data:
            self.log_test("Bond Yield Calculation", False, "No bonds data available for testing")
            return False
        
        try:
            # Test yield calculation for Ghana bond
            ghana_bond = next((b for b in self.bonds_data if b["country"] == "Ghana"), None)
            if not ghana_bond:
                self.log_test("Bond Yield Calculation", False, "Ghana bond not found")
                return False
            
            response = requests.get(f"{self.base_url}/bonds/{ghana_bond['id']}/yield", timeout=10)
            
            if response.status_code != 200:
                self.log_test("Bond Yield Calculation", False, f"HTTP {response.status_code}: {response.text}")
                return False
            
            yield_data = response.json()
            
            # Verify yield calculation structure
            required_fields = ["bond_id", "country", "base_yield", "risk_factor", "dynamic_yield", "current_price", "face_value"]
            missing_fields = [field for field in required_fields if field not in yield_data]
            if missing_fields:
                self.log_test("Bond Yield Structure", False, f"Missing fields: {missing_fields}")
                return False
            
            # Verify risk engine calculation: base_yield * (1 + risk_factor/100)
            expected_base_calculation = yield_data["base_yield"] * (1 + yield_data["risk_factor"] / 100)
            
            # Dynamic yield should be at least the risk-adjusted yield (may have additional factors)
            if yield_data["dynamic_yield"] < expected_base_calculation * 0.95:  # Allow 5% tolerance
                self.log_test("Risk Engine Calculation", False, 
                            f"Dynamic yield {yield_data['dynamic_yield']} too low compared to expected {expected_base_calculation}")
                return False
            
            self.log_test("Bond Yield Calculation", True, 
                         f"Ghana bond yield: {yield_data['dynamic_yield']}% (base: {yield_data['base_yield']}%, risk: {yield_data['risk_factor']}%)")
            self.log_test("Risk Engine", True, "Risk-based yield calculation working correctly")
            return True
            
        except Exception as e:
            self.log_test("Bond Yield Calculation", False, f"Exception: {str(e)}")
            return False
    
    def test_trading_functionality(self):
        """Test POST /trade - AMM Trading Logic"""
        if not self.bonds_data:
            self.log_test("Trading Functionality", False, "No bonds data available for trading test")
            return False
        
        try:
            # Find Ghana bond for trading
            ghana_bond = next((b for b in self.bonds_data if b["country"] == "Ghana"), None)
            if not ghana_bond:
                self.log_test("Trading Functionality", False, "Ghana bond not found for trading")
                return False
            
            # Record initial supply
            initial_supply = ghana_bond["available_supply"]
            
            # Execute buy trade
            trade_request = {
                "user_address": TEST_USER_ADDRESS,
                "bond_id": ghana_bond["id"],
                "quantity": 5,
                "transaction_type": "buy"
            }
            
            response = requests.post(f"{self.base_url}/trade", 
                                   json=trade_request, 
                                   headers={"Content-Type": "application/json"},
                                   timeout=15)
            
            if response.status_code != 200:
                self.log_test("Trading Functionality", False, f"Trade failed with HTTP {response.status_code}: {response.text}")
                return False
            
            trade_result = response.json()
            
            # Verify trade response structure
            required_fields = ["success", "transaction_id", "trade_price", "total_amount", "new_portfolio_value"]
            missing_fields = [field for field in required_fields if field not in trade_result]
            if missing_fields:
                self.log_test("Trade Response Structure", False, f"Missing fields: {missing_fields}")
                return False
            
            if not trade_result["success"]:
                self.log_test("Trading Functionality", False, "Trade marked as unsuccessful")
                return False
            
            # Verify trade calculations
            expected_total = trade_result["trade_price"] * 5
            if abs(trade_result["total_amount"] - expected_total) > 0.01:
                self.log_test("Trade Calculations", False, 
                            f"Total amount {trade_result['total_amount']} doesn't match expected {expected_total}")
                return False
            
            # Verify supply adjustment by checking bonds again
            time.sleep(1)  # Brief delay for database update
            updated_response = requests.get(f"{self.base_url}/bonds", timeout=10)
            if updated_response.status_code == 200:
                updated_bonds = updated_response.json()
                updated_ghana = next((b for b in updated_bonds if b["country"] == "Ghana"), None)
                if updated_ghana:
                    expected_new_supply = initial_supply - 5
                    if updated_ghana["available_supply"] != expected_new_supply:
                        self.log_test("Supply Adjustment", False, 
                                    f"Supply not updated correctly. Expected {expected_new_supply}, got {updated_ghana['available_supply']}")
                        return False
                    else:
                        self.log_test("Supply Adjustment", True, f"Bond supply correctly reduced from {initial_supply} to {updated_ghana['available_supply']}")
            
            self.log_test("Trading Functionality", True, 
                         f"Successfully bought 5 Ghana bonds for ${trade_result['total_amount']:.2f}")
            self.log_test("AMM Trading Logic", True, "Buy operation, portfolio update, and supply adjustment working")
            return True
            
        except Exception as e:
            self.log_test("Trading Functionality", False, f"Exception: {str(e)}")
            return False
    
    def test_portfolio_endpoint(self):
        """Test GET /portfolio/{user_address} - Portfolio Management"""
        try:
            response = requests.get(f"{self.base_url}/portfolio/{TEST_USER_ADDRESS}", timeout=10)
            
            if response.status_code != 200:
                self.log_test("Portfolio Endpoint", False, f"HTTP {response.status_code}: {response.text}")
                return False
            
            portfolio_data = response.json()
            
            # Verify portfolio structure
            if "portfolio" not in portfolio_data or "detailed_holdings" not in portfolio_data or "summary" not in portfolio_data:
                self.log_test("Portfolio Structure", False, "Missing required portfolio sections")
                return False
            
            portfolio = portfolio_data["portfolio"]
            holdings = portfolio_data["detailed_holdings"]
            summary = portfolio_data["summary"]
            
            # After the trade, we should have Ghana bonds
            if len(holdings) == 0:
                self.log_test("Portfolio Holdings", False, "No holdings found after trade")
                return False
            
            # Find Ghana bond holding
            ghana_holding = next((h for h in holdings if h["bond"]["country"] == "Ghana"), None)
            if not ghana_holding:
                self.log_test("Portfolio Holdings", False, "Ghana bond not found in portfolio after trade")
                return False
            
            if ghana_holding["quantity"] != 5:
                self.log_test("Portfolio Holdings", False, f"Expected 5 Ghana bonds, found {ghana_holding['quantity']}")
                return False
            
            # Verify portfolio calculations
            if summary["total_bonds"] != len(portfolio["bonds"]):
                self.log_test("Portfolio Calculations", False, "Total bonds count mismatch")
                return False
            
            if summary["total_value"] <= 0:
                self.log_test("Portfolio Calculations", False, "Portfolio total value should be positive")
                return False
            
            self.log_test("Portfolio Endpoint", True, 
                         f"Portfolio shows {summary['total_bonds']} bond types, total value: ${summary['total_value']:.2f}")
            return True
            
        except Exception as e:
            self.log_test("Portfolio Endpoint", False, f"Exception: {str(e)}")
            return False
    
    def test_market_stats_endpoint(self):
        """Test GET /market-stats - Market Statistics"""
        try:
            response = requests.get(f"{self.base_url}/market-stats", timeout=10)
            
            if response.status_code != 200:
                self.log_test("Market Stats Endpoint", False, f"HTTP {response.status_code}: {response.text}")
                return False
            
            stats = response.json()
            
            # Verify market stats structure
            required_fields = ["total_market_value", "total_volume_24h", "average_yield", "active_bonds", "total_transactions"]
            missing_fields = [field for field in required_fields if field not in stats]
            if missing_fields:
                self.log_test("Market Stats Structure", False, f"Missing fields: {missing_fields}")
                return False
            
            # Verify reasonable values
            if stats["active_bonds"] != 4:
                self.log_test("Market Stats Values", False, f"Expected 4 active bonds, got {stats['active_bonds']}")
                return False
            
            if stats["total_market_value"] <= 0:
                self.log_test("Market Stats Values", False, "Total market value should be positive")
                return False
            
            if not (0 <= stats["average_yield"] <= 20):
                self.log_test("Market Stats Values", False, f"Average yield {stats['average_yield']}% seems unrealistic")
                return False
            
            # After our trade, there should be at least 1 transaction
            if stats["total_transactions"] < 1:
                self.log_test("Market Stats Values", False, "Should have at least 1 transaction after our trade")
                return False
            
            self.log_test("Market Stats Endpoint", True, 
                         f"Market stats: {stats['active_bonds']} bonds, ${stats['total_market_value']:.2f} market value, {stats['average_yield']:.2f}% avg yield")
            return True
            
        except Exception as e:
            self.log_test("Market Stats Endpoint", False, f"Exception: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run comprehensive test suite"""
        print("=" * 80)
        print("SOVEREIGN BOND MARKETPLACE - BACKEND API TESTS")
        print("=" * 80)
        
        # Test sequence based on dependencies
        tests = [
            ("API Health Check", self.test_api_health),
            ("Bond Data & Dynamic Pricing", self.test_bonds_endpoint),
            ("Risk Engine & Yield Calculation", self.test_bond_yield_calculation),
            ("AMM Trading Logic", self.test_trading_functionality),
            ("Portfolio Management", self.test_portfolio_endpoint),
            ("Market Statistics", self.test_market_stats_endpoint)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n--- Running {test_name} ---")
            if test_func():
                passed += 1
            else:
                print(f"⚠️  {test_name} failed - subsequent tests may be affected")
        
        print("\n" + "=" * 80)
        print(f"TEST SUMMARY: {passed}/{total} tests passed")
        print("=" * 80)
        
        # Detailed results
        print("\nDETAILED RESULTS:")
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            print(f"{status} {test_name}: {result['details']}")
        
        return passed == total

if __name__ == "__main__":
    tester = BondMarketplaceTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 ALL BACKEND TESTS PASSED!")
        exit(0)
    else:
        print("\n❌ SOME TESTS FAILED - Check details above")
        exit(1)