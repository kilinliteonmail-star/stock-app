import streamlit as st
import yfinance as yf
import pandas as pd
import mplfinance as mpf
import numpy as np

# --- 1. 網頁標題與輸入區塊 ---
st.set_page_config(page_title="均線扣抵戰情室", layout="wide")
st.title("📈 均線扣抵戰情室 (K線視覺化)")

stock_symbol = st.text_input("🔍 請輸入股票代號 (例如: 2330.TW, 2603.TW, AAPL):", "2330.TW")

# --- 2. 資料下載與運算區塊 ---
if stock_symbol:
    with st.spinner(f"正在下載 {stock_symbol} 的歷史資料與計算扣抵值..."):
        try:
            # 💡 修正 1：改用 yf.Ticker().history() 確保回傳單層乾淨的 DataFrame
            # 這能避開 yf.download() 新版容易產生的 MultiIndex 格式錯亂問題
            ticker = yf.Ticker(stock_symbol)
            df = ticker.history(period='2y')
            
            if df.empty:
                st.error("找不到該股票資料，請確認代號是否正確。")
            else:
                # 確保時間軸時區一致，避免 mplfinance 報錯
                df.index = df.index.tz_localize(None)

                # 計算均線與扣抵
                df['MA60'] = df['Close'].rolling(window=60).mean()
                df['MA120'] = df['Close'].rolling(window=120).mean()
                df['MA240'] = df['Close'].rolling(window=240).mean()
                df['Deduction60'] = df['Close'].shift(60) # 60日扣抵防線

                # 計算買賣訊號
                buy_cond1 = (df['MA60'] > df['MA120']) & (df['MA120'] > df['MA240'])
                buy_cond2 = df['Close'] > df['Deduction60']
                buy_signal = buy_cond1 & buy_cond2
                sell_signal = df['Close'] < (df['Deduction60'] * 0.98)

                # 💡 修正 2：先截取最後 250 天的 DataFrame，再製作對應的空 Series
                # 這樣能保證畫圖的圖層 (addplot) 和 K 線圖 (plot_df) 的 Index 完全對齊！
                plot_df = df.iloc[-250:].copy()
                
                # 建立完全充滿 NaN 的 Series，並綁定相同的 Index
                plot_buy = pd.Series(np.nan, index=plot_df.index)
                plot_sell = pd.Series(np.nan, index=plot_df.index)

                # 把最近 250 天的布林訊號取出來
                signal_buy_250 = buy_signal.iloc[-250:]
                signal_sell_250 = sell_signal.iloc[-250:]

                # 只有符合條件的日子，才填入股價位置 (畫箭頭用)
                plot_buy[signal_buy_250] = plot_df['Low'][signal_buy_250] * 0.97
                plot_sell[signal_sell_250] = plot_df['High'][signal_sell_250] * 1.03

                # --- 3. 繪製圖表並顯示在網頁上 ---
                apds = [
                    mpf.make_addplot(plot_df['MA60'], color='orange', width=1.5),
                    mpf.make_addplot(plot_df['MA120'], color='green', width=1.5, linestyle='--'),
                    mpf.make_addplot(plot_df['MA240'], color='blue', width=1.5, linestyle=':'),
                    mpf.make_addplot(plot_df['Deduction60'], color='gray', linestyle='-.', width=1.0),
                    mpf.make_addplot(plot_buy, type='scatter', markersize=100, marker='^', color='red'),
                    mpf.make_addplot(plot_sell, type='scatter', markersize=100, marker='v', color='green'),
                ]

                my_style = mpf.make_mpf_style(base_mpf_style='yahoo', rc={'font.size': 10})
                
                fig, axlist = mpf.plot(
                    plot_df, type='candle', style=my_style, addplot=apds,
                    volume=True, title=f"{stock_symbol} 戰情圖",
                    figsize=(14, 7), tight_layout=True, returnfig=True
                )
                
                # 在網頁上顯示圖表
                st.pyplot(fig)
                
                # 顯示最新的數據狀態
                st.markdown("### 📊 最新數據狀態")
                latest = plot_df.iloc[-1]
                col1, col2, col3 = st.columns(3)
                col1.metric("今日收盤價", f"{latest['Close']:.2f}")
                col2.metric("60日扣抵價 (防線)", f"{latest['Deduction60']:.2f}")
                
                if latest['Close'] > latest['Deduction60']:
                    col3.success("🟢 目前大於扣抵值，季線助漲中！")
                else:
                    col3.error("🔴 目前小於扣抵值，注意季線下彎壓力！")

        except Exception as e:
            st.error(f"發生錯誤：{e}")
