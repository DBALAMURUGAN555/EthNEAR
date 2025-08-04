import React, { useState, useEffect } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Mock user address for demo
const DEMO_USER_ADDRESS = "0x1234567890abcdef1234567890abcdef12345678";

function App() {
  const [bonds, setBonds] = useState([]);
  const [portfolio, setPortfolio] = useState(null);
  const [marketStats, setMarketStats] = useState(null);
  const [activeTab, setActiveTab] = useState('market');
  const [loading, setLoading] = useState(false);
  const [selectedBond, setSelectedBond] = useState(null);
  const [tradeQuantity, setTradeQuantity] = useState(1);
  const [showTradeModal, setShowTradeModal] = useState(false);

  // Fetch data functions
  const fetchBonds = async () => {
    try {
      const response = await axios.get(`${API}/bonds`);
      setBonds(response.data);
    } catch (error) {
      console.error('Error fetching bonds:', error);
    }
  };

  const fetchPortfolio = async () => {
    try {
      const response = await axios.get(`${API}/portfolio/${DEMO_USER_ADDRESS}`);
      setPortfolio(response.data);
    } catch (error) {
      console.error('Error fetching portfolio:', error);
    }
  };

  const fetchMarketStats = async () => {
    try {
      const response = await axios.get(`${API}/market-stats`);
      setMarketStats(response.data);
    } catch (error) {
      console.error('Error fetching market stats:', error);
    }
  };

  const executeTrade = async (bondId, quantity, type) => {
    setLoading(true);
    try {
      const response = await axios.post(`${API}/trade`, {
        user_address: DEMO_USER_ADDRESS,
        bond_id: bondId,
        quantity: parseFloat(quantity),
        transaction_type: type
      });
      
      if (response.data.success) {
        alert(`Trade successful! Transaction ID: ${response.data.transaction_id}`);
        fetchBonds();
        fetchPortfolio();
        fetchMarketStats();
        setShowTradeModal(false);
        setTradeQuantity(1);
      }
    } catch (error) {
      alert('Trade failed: ' + (error.response?.data?.detail || error.message));
    }
    setLoading(false);
  };

  const openTradeModal = (bond) => {
    setSelectedBond(bond);
    setShowTradeModal(true);
  };

  useEffect(() => {
    fetchBonds();
    fetchPortfolio();
    fetchMarketStats();
    
    // Refresh data every 30 seconds
    const interval = setInterval(() => {
      fetchBonds();
      fetchMarketStats();
    }, 30000);
    
    return () => clearInterval(interval);
  }, []);

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  };

  const getRiskColor = (riskFactor) => {
    if (riskFactor < 2) return 'text-green-600 bg-green-100';
    if (riskFactor < 4) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  const getYieldColor = (yield_value) => {
    if (yield_value > 8) return 'text-green-600 font-bold';
    if (yield_value > 6) return 'text-blue-600 font-semibold';
    return 'text-gray-600';
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-lg border-b-4 border-blue-600">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <h1 className="text-3xl font-bold text-gray-900">SovereignFi</h1>
                <p className="text-sm text-gray-600">Democratizing Sovereign Debt Markets</p>
              </div>
            </div>
            <div className="hidden md:block">
              <div className="ml-10 flex items-baseline space-x-4">
                <button
                  onClick={() => setActiveTab('market')}
                  className={`px-3 py-2 rounded-md text-sm font-medium ${
                    activeTab === 'market'
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  Bond Market
                </button>
                <button
                  onClick={() => setActiveTab('portfolio')}
                  className={`px-3 py-2 rounded-md text-sm font-medium ${
                    activeTab === 'portfolio'
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  My Portfolio
                </button>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <div className="relative bg-gradient-to-r from-blue-800 to-blue-600 text-white">
        <div className="absolute inset-0">
          <img
            className="w-full h-full object-cover opacity-20"
            src="https://images.unsplash.com/flagged/photo-1579225818168-858da8667fae?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1Nzh8MHwxfHNlYXJjaHwxfHxmaW5hbmNpYWwlMjB0cmFkaW5nfGVufDB8fHx8MTc1NDMzMTgxN3ww&ixlib=rb-4.1.0&q=85"
            alt="Financial Trading"
          />
        </div>
        <div className="relative max-w-7xl mx-auto py-16 px-4 sm:py-24 sm:px-6 lg:px-8">
          <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl lg:text-6xl">
            Trade Sovereign Bonds
          </h1>
          <p className="mt-6 text-xl max-w-3xl">
            Access institutional-grade sovereign debt markets with dynamic risk pricing,
            transparent yields, and DeFi liquidity. Minimum investment: $100.
          </p>
          {marketStats && (
            <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div className="bg-white bg-opacity-20 rounded-lg p-4">
                <div className="text-2xl font-bold">{formatCurrency(marketStats.total_market_value)}</div>
                <div className="text-sm opacity-90">Total Market Value</div>
              </div>
              <div className="bg-white bg-opacity-20 rounded-lg p-4">
                <div className="text-2xl font-bold">{marketStats.average_yield.toFixed(1)}%</div>
                <div className="text-sm opacity-90">Average Yield</div>
              </div>
              <div className="bg-white bg-opacity-20 rounded-lg p-4">
                <div className="text-2xl font-bold">{marketStats.active_bonds}</div>
                <div className="text-sm opacity-90">Active Bonds</div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
        {activeTab === 'market' && (
          <div>
            <div className="mb-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">Available Sovereign Bonds</h2>
              <p className="text-gray-600 mb-6">
                Dynamic yields adjust in real-time based on country risk, supply scarcity, and market demand.
              </p>
            </div>

            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-2">
              {bonds.map((bond) => (
                <div key={bond.id} className="bg-white rounded-lg shadow-lg overflow-hidden">
                  <div className="bg-gradient-to-r from-gray-50 to-blue-50 px-6 py-4">
                    <div className="flex justify-between items-start">
                      <div>
                        <h3 className="text-xl font-bold text-gray-900">
                          {bond.country} {bond.maturity_date.split('-')[0]}
                        </h3>
                        <p className="text-sm text-gray-600">{bond.country_code} Sovereign Bond</p>
                      </div>
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getRiskColor(bond.risk_factor)}`}>
                        Risk: {bond.risk_factor}%
                      </span>
                    </div>
                  </div>
                  
                  <div className="px-6 py-4">
                    <div className="grid grid-cols-2 gap-4 mb-4">
                      <div>
                        <p className="text-sm text-gray-500">Current Price</p>
                        <p className="text-lg font-semibold text-gray-900">{formatCurrency(bond.current_price)}</p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-500">Face Value</p>
                        <p className="text-lg font-semibold text-gray-900">{formatCurrency(bond.face_value)}</p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-500">Base Coupon</p>
                        <p className="text-lg font-semibold text-blue-600">{bond.coupon_rate}%</p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-500">Dynamic Yield</p>
                        <p className={`text-lg font-semibold ${getYieldColor(bond.coupon_rate * (1 + bond.risk_factor / 100))}`}>
                          {(bond.coupon_rate * (1 + bond.risk_factor / 100)).toFixed(1)}%
                        </p>
                      </div>
                    </div>
                    
                    <div className="mb-4">
                      <div className="flex justify-between text-sm text-gray-600 mb-1">
                        <span>Available Supply</span>
                        <span>{bond.available_supply.toLocaleString()} / {bond.total_supply.toLocaleString()}</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-blue-600 h-2 rounded-full"
                          style={{ width: `${(bond.available_supply / bond.total_supply) * 100}%` }}
                        ></div>
                      </div>
                    </div>
                    
                    <div className="text-xs text-gray-500 mb-4">
                      Maturity: {new Date(bond.maturity_date).toLocaleDateString()}
                    </div>
                    
                    <button
                      onClick={() => openTradeModal(bond)}
                      className="w-full bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 transition-colors font-medium"
                    >
                      Trade Bond
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'portfolio' && (
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-6">My Portfolio</h2>
            
            {portfolio && portfolio.detailed_holdings && portfolio.detailed_holdings.length > 0 ? (
              <div>
                <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="text-center">
                      <p className="text-3xl font-bold text-blue-600">{formatCurrency(portfolio.portfolio.total_value)}</p>
                      <p className="text-sm text-gray-600">Total Portfolio Value</p>
                    </div>
                    <div className="text-center">
                      <p className="text-3xl font-bold text-green-600">{portfolio.portfolio.total_yield.toFixed(1)}%</p>
                      <p className="text-sm text-gray-600">Average Yield</p>
                    </div>
                    <div className="text-center">
                      <p className="text-3xl font-bold text-gray-900">{portfolio.summary.total_bonds}</p>
                      <p className="text-sm text-gray-600">Bond Types</p>
                    </div>
                  </div>
                </div>

                <div className="grid gap-4">
                  {portfolio.detailed_holdings.map((holding, index) => (
                    <div key={index} className="bg-white rounded-lg shadow p-6">
                      <div className="flex justify-between items-start mb-4">
                        <div>
                          <h3 className="text-lg font-semibold text-gray-900">
                            {holding.bond.country} {holding.bond.maturity_date.split('-')[0]}
                          </h3>
                          <p className="text-sm text-gray-600">Quantity: {holding.quantity} bonds</p>
                        </div>
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getRiskColor(holding.bond.risk_factor)}`}>
                          {holding.bond.risk_factor}% Risk
                        </span>
                      </div>
                      
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div>
                          <p className="text-sm text-gray-500">Current Value</p>
                          <p className="text-lg font-semibold text-gray-900">{formatCurrency(holding.current_value)}</p>
                        </div>
                        <div>
                          <p className="text-sm text-gray-500">Dynamic Yield</p>
                          <p className={`text-lg font-semibold ${getYieldColor(holding.dynamic_yield)}`}>
                            {holding.dynamic_yield}%
                          </p>
                        </div>
                        <div>
                          <p className="text-sm text-gray-500">Unrealized P&L</p>
                          <p className={`text-lg font-semibold ${holding.unrealized_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {formatCurrency(holding.unrealized_pnl)}
                          </p>
                        </div>
                        <div>
                          <button
                            onClick={() => openTradeModal(holding.bond)}
                            className="bg-gray-100 text-gray-700 py-1 px-3 rounded hover:bg-gray-200 transition-colors text-sm"
                          >
                            Trade
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="text-center py-12">
                <img
                  className="mx-auto h-32 w-32 text-gray-400 opacity-50"
                  src="https://images.unsplash.com/photo-1635236269483-7e5d494e0097?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1Nzh8MHwxfHNlYXJjaHwyfHxmaW5hbmNpYWwlMjB0cmFkaW5nfGVufDB8fHx8MTc1NDMzMTgxN3ww&ixlib=rb-4.1.0&q=85"
                  alt="Empty Portfolio"
                />
                <h3 className="mt-4 text-lg font-medium text-gray-900">No bonds in portfolio</h3>
                <p className="mt-2 text-gray-500">Start trading sovereign bonds to build your portfolio.</p>
                <button
                  onClick={() => setActiveTab('market')}
                  className="mt-4 bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Browse Bonds
                </button>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Trade Modal */}
      {showTradeModal && selectedBond && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div className="mt-3">
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                Trade {selectedBond.country} {selectedBond.maturity_date.split('-')[0]} Bond
              </h3>
              
              <div className="mb-4">
                <p className="text-sm text-gray-600 mb-2">Current Price: {formatCurrency(selectedBond.current_price)}</p>
                <p className="text-sm text-gray-600 mb-2">Available: {selectedBond.available_supply} bonds</p>
              </div>
              
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Quantity
                </label>
                <input
                  type="number"
                  min="1"
                  max={selectedBond.available_supply}
                  value={tradeQuantity}
                  onChange={(e) => setTradeQuantity(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              
              <div className="mb-4">
                <p className="text-sm text-gray-600">
                  Total Cost: {formatCurrency(selectedBond.current_price * tradeQuantity)}
                </p>
              </div>
              
              <div className="flex space-x-3">
                <button
                  onClick={() => executeTrade(selectedBond.id, tradeQuantity, 'buy')}
                  disabled={loading}
                  className="flex-1 bg-green-600 text-white py-2 px-4 rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
                >
                  {loading ? 'Processing...' : 'Buy'}
                </button>
                <button
                  onClick={() => executeTrade(selectedBond.id, tradeQuantity, 'sell')}
                  disabled={loading}
                  className="flex-1 bg-red-600 text-white py-2 px-4 rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
                >
                  {loading ? 'Processing...' : 'Sell'}
                </button>
              </div>
              
              <button
                onClick={() => {
                  setShowTradeModal(false);
                  setTradeQuantity(1);
                }}
                className="w-full mt-3 bg-gray-300 text-gray-700 py-2 px-4 rounded-lg hover:bg-gray-400 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;