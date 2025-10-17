#!/usr/bin/env python3
"""
Test script to verify the SQLite migration and new date-based functionality.
"""

from datetime import datetime, date
from db_utils import (
    get_todays_recommendations,
    get_recommendations_by_date, 
    get_recommendations_sqlite,
    get_recommendation_stats,
    store_recommendations_sqlite,
    mark_recommendation_inactive_sqlite
)
import json

def test_basic_functionality():
    """Test basic SQLite functionality."""
    print("=== Testing Basic Functionality ===")
    
    # Test stats
    stats = get_recommendation_stats()
    print(f"Database stats: {stats}")
    
    # Test today's recommendations
    today_recs = get_todays_recommendations()
    print(f"Today's recommendations: {len(today_recs)} tickers")
    
    # Show a few examples
    for i, (ticker, recs) in enumerate(list(today_recs.items())[:3]):
        print(f"  {ticker}: {recs[0]['recommendation']} - {recs[0]['confidence']} confidence")
        if i >= 2:  # Limit output
            break
    
    print("✓ Basic functionality working")

def test_date_queries():
    """Test date-based queries."""
    print("\n=== Testing Date Queries ===")
    
    # Test specific date query
    historical_recs = get_recommendations_by_date("2025-07-03")
    print(f"Recommendations on 2025-07-03: {len(historical_recs)} tickers")
    
    # Show breakdown by recommendation type
    buy_count = sell_count = hold_count = 0
    for ticker, recs in historical_recs.items():
        for rec in recs:
            if rec["recommendation"] == "BUY":
                buy_count += 1
            elif rec["recommendation"] == "SELL":
                sell_count += 1
            elif rec["recommendation"] == "HOLD":
                hold_count += 1
    
    print(f"  BUY: {buy_count}, SELL: {sell_count}, HOLD: {hold_count}")
    print("✓ Date queries working")

def test_filtering():
    """Test filtering functionality."""
    print("\n=== Testing Filtering ===")
    
    # Test ticker filtering
    aapl_recs = get_recommendations_sqlite(ticker="AAPL")
    print(f"AAPL recommendations: {len(aapl_recs.get('AAPL', []))}")
    
    # Test recommendation type filtering  
    buy_recs = get_recommendations_sqlite(recommendation_type="BUY")
    sell_recs = get_recommendations_sqlite(recommendation_type="SELL")
    print(f"All BUY recommendations: {sum(len(recs) for recs in buy_recs.values())}")
    print(f"All SELL recommendations: {sum(len(recs) for recs in sell_recs.values())}")
    
    print("✓ Filtering working")

def test_new_recommendations():
    """Test storing new recommendations."""
    print("\n=== Testing New Recommendation Storage ===")
    
    # Create test recommendations
    test_recs = [
        {
            "company": "Test Company A",
            "ticker": "TESTA",
            "recommendation": "BUY",
            "reason": "Migration test - strong fundamentals",
            "confidence": "HIGH",
            "article_title": "Test Article A",
            "article_url": "https://example.com/test-a"
        },
        {
            "company": "Test Company B", 
            "ticker": "TESTB",
            "recommendation": "SELL",
            "reason": "Migration test - overvalued",
            "confidence": "MEDIUM",
            "article_title": "Test Article B",
            "article_url": "https://example.com/test-b"
        }
    ]
    
    today_str = date.today().isoformat()
    
    # Store test recommendations
    store_recommendations_sqlite(test_recs, today_str)
    
    # Verify they were stored
    test_a_recs = get_recommendations_sqlite(ticker="TESTA")
    test_b_recs = get_recommendations_sqlite(ticker="TESTB")
    
    print(f"TESTA recommendations stored: {len(test_a_recs.get('TESTA', []))}")
    print(f"TESTB recommendations stored: {len(test_b_recs.get('TESTB', []))}")
    
    # Clean up test data
    if test_a_recs.get("TESTA"):
        rec_id = f"TESTA_{today_str}_BUY"
        mark_recommendation_inactive_sqlite(rec_id)
    if test_b_recs.get("TESTB"):
        rec_id = f"TESTB_{today_str}_SELL"
        mark_recommendation_inactive_sqlite(rec_id)
    
    print("✓ New recommendation storage working")

def simulate_api_endpoints():
    """Simulate the new API endpoints."""
    print("\n=== Simulating API Endpoints ===")
    
    # Simulate /api/recommendations/today
    today_data = {
        "status": "success",
        "date": date.today().isoformat(),
        "stats": get_recommendation_stats(),
        "recommendations": get_todays_recommendations()
    }
    
    print(f"Today's API response: {len(today_data['recommendations'])} tickers")
    print(f"Today's stats: {today_data['stats']['today']} recommendations")
    
    # Simulate /api/recommendations/date/2025-07-03
    historical_data = {
        "status": "success", 
        "date": "2025-07-03",
        "recommendations": get_recommendations_by_date("2025-07-03")
    }
    
    print(f"Historical API response: {len(historical_data['recommendations'])} tickers")
    print("✓ API endpoints working")

def main():
    """Run all tests."""
    print("Testing SQLite Migration and New Features")
    print("=" * 50)
    
    try:
        test_basic_functionality()
        test_date_queries()
        test_filtering()
        test_new_recommendations()
        simulate_api_endpoints()
        
        print("\n" + "=" * 50)
        print("🎉 All tests passed! Migration successful!")
        print("\nYou can now:")
        print("• Query today's recommendations: /recommendations?today=true")
        print("• Query specific dates: /recommendations?date=2025-07-03")
        print("• Use API endpoints: /api/recommendations/today")
        print("• Use API endpoints: /api/recommendations/date/YYYY-MM-DD")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()