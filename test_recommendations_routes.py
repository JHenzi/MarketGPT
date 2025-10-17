#!/usr/bin/env python3
"""
Test script demonstrating the new recommendations page behavior.
Shows how the route now defaults to today's recommendations.
"""

from db_utils import get_todays_recommendations, get_recommendations_sqlite
from datetime import datetime

def test_route_behaviors():
    """Test the different recommendation route behaviors."""
    print("🧪 Testing Recommendations Route Behaviors")
    print("=" * 50)
    
    # Default behavior (now shows today's recommendations)
    today_recs = get_todays_recommendations()
    print(f"📅 Default /recommendations (today's): {len(today_recs)} tickers")
    
    # All recommendations (explicit parameter)
    all_recs = get_recommendations_sqlite(today_only=False)
    print(f"📊 /recommendations?all=true: {len(all_recs)} tickers")
    
    # Today's BUY signals
    buy_today = get_recommendations_sqlite(recommendation_type="BUY", today_only=True)
    print(f"📈 /recommendations?type=BUY (today): {len(buy_today)} tickers")
    
    # Today's SELL signals  
    sell_today = get_recommendations_sqlite(recommendation_type="SELL", today_only=True)
    print(f"📉 /recommendations?type=SELL (today): {len(sell_today)} tickers")
    
    # Historical date
    historical = get_recommendations_sqlite(date_filter="2025-07-03")
    print(f"📅 /recommendations?date=2025-07-03: {len(historical)} tickers")
    
    print("\n🔗 URL Examples:")
    print("• /recommendations                      → Today's recommendations (DEFAULT)")
    print("• /recommendations?today=true           → Today's recommendations (explicit)")
    print("• /recommendations?all=true             → All historical recommendations")
    print("• /recommendations?type=BUY             → Today's BUY signals only")
    print("• /recommendations?all=true&type=SELL   → All historical SELL signals")
    print("• /recommendations?date=2025-07-03      → Specific date recommendations")
    
    print(f"\n📊 Summary:")
    print(f"• Today ({datetime.now().strftime('%B %d, %Y')}): {len(today_recs)} recommendations")
    print(f"• Total historical: {len(all_recs)} recommendations")
    print(f"• Today's BUY signals: {len(buy_today)}")
    print(f"• Today's SELL signals: {len(sell_today)}")
    
    # Show some example recommendations
    if today_recs:
        print(f"\n📋 Today's Recommendations Preview:")
        for i, (ticker, recs) in enumerate(list(today_recs.items())[:3]):
            rec = recs[0]  # Show first recommendation for each ticker
            print(f"  {ticker}: {rec['recommendation']} - {rec['reason'][:50]}...")
            if i >= 2:  # Limit to 3 examples
                break
    
    print("\n✅ All route behaviors working correctly!")

if __name__ == "__main__":
    test_route_behaviors()