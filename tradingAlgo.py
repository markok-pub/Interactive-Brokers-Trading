import flasktrader.accountInfo as AccountInfo
import flasktrader.buyingScript as Buying
import flasktrader.marketData as Data
import flasktrader.getContractExp as Contracts
from flasktrader import db
from flasktrader.models import Bought, Sold
import datetime
from ibapi.contract import Contract as IBcontract
from ibapi.order import Order
import time
import pandas as pd


def getExpirationDates(symbol, currency, exchange, callOrPut, multiplier, date):

	app = Contracts.TestApp("127.0.0.1", 7497, 777)

	## lets get prices for this

	ibcontract = IBcontract()
	ibcontract.symbol = symbol
	ibcontract.secType = "OPT"
	ibcontract.currency = currency
	ibcontract.exchange = exchange

	ibcontract.right = callOrPut
	ibcontract.multiplier = multiplier

	if(date != "false"):
		ibcontract.lastTradeDateOrContractMonth = date

    ## resolve the contract
	(list_of_dates, strikes, list_of_contracts) = app.resolve_ib_contract(ibcontract)

	#print(list_of_dates[0])

	app.disconnect()

	return (list_of_dates, strikes, list_of_contracts)

def getAccountInfo():

	app = AccountInfo.TestApp("127.0.0.1", 7497, 333)

    ## lets get positions
	positions_list = app.get_current_positions()
    ##print("positions: ")
	#print(positions_list)

    ## get the account name from the position
    ## normally you would know your account name

	try:
		accountName = positions_list[0][0]
	except:
		return (positions_list, None, None, 0)
		app.disconnect()
    ## and accounting information
	accounting_values = app.get_accounting_values(accountName)
    #print("accounting values ")
    #print(accounting_values)

	funds = 0
    #print("accounting values ")
	for val in accounting_values:
		if(val[0] == "AvailableFunds"):
			funds = val[1]
            #print(funds)

    ## these values are cached
    ## if we ask again in more than 5 minutes it will update everything
	##accounting_updates = app.get_accounting_updates(accountName)
    ##print("accounting updates ")
    ##print(accounting_updates)

	app.disconnect()

	return (positions_list, accounting_values, None, funds)

## ADD MORE FOR OPTIONS AND FUTURES
def transaction(symbol, secType, currency, exchange, primaryExchange, contractExp, orderAction, orderType, totalQuantity, callOrPut, priceType, strikePrice, multiplier, tradingClass):

	app = Buying.TestApp("127.0.0.1", 7497, 666)

	## lets get prices for this

	ibcontract = IBcontract()
	ibcontract.symbol = symbol
	ibcontract.secType = secType
	ibcontract.currency = currency
	ibcontract.exchange = exchange

	if(secType == "STK"):
		ibcontract.primaryExchange = primaryExchange

	elif(secType == "OPT"):
		ibcontract.lastTradeDateOrContractMonth = contractExp
		ibcontract.strike = strikePrice
		ibcontract.right = callOrPut
		ibcontract.multiplier = multiplier
	elif(secType == "FUT"):
		ibcontract.tradingClass = tradingClass


    ## resolve the contract
	resolved_ibcontract = app.resolve_ib_contract(ibcontract)

	order = Order()
	order.action = orderAction
	order.orderType = orderType
	order.totalQuantity = totalQuantity
	order.transmit = True

    ## place the order
	orderid = app.place_new_IB_order(resolved_ibcontract, order, orderid=None)

    #print("Placed market order, orderid is %d" % orderid1)

	#while app.any_open_orders():
        ## Warning this will pause forever if fill doesn't come back
		#time.sleep(1)

    ## Have a look at the fill
    #print("Recent fills")
	filldetails = app.recent_fills_and_commissions()
	print(filldetails)

    ## but this won't be
    #print("Executions today")
	#execdetails = app.get_executions_and_commissions()
    #print(execdetails)

	#open_orders = app.get_open_orders()

	app.disconnect()

	return orderid


def getData(symbol, secType, currency, exchange, primaryExchange, contractExp, strike, callOrPut, multiplier, tradingClass):

	app = Data.TestApp("127.0.0.1", 7497, 999)

	ibcontract = IBcontract()
	ibcontract.symbol=symbol
	ibcontract.secType = secType
	ibcontract.currency = currency
	ibcontract.exchange=exchange

	if(secType == "STK"):
		ibcontract.primaryExchange = primaryExchange

	elif(secType == "OPT"):
		ibcontract.lastTradeDateOrContractMonth = contractExp
		ibcontract.strike = strike
		ibcontract.right = callOrPut
		ibcontract.multiplier = multiplier
	
	elif(secType == "FUT"):
		ibcontract.trading_class = tradingClass

	## resolve the contract
	resolved_ibcontract = app.resolve_ib_contract(ibcontract)

	tickerid = app.start_getting_IB_market_data(resolved_ibcontract)

	time.sleep(0.5)

	## What have we got so far?
	market_data = app.get_IB_market_data(tickerid)

	market_data1_as_df = market_data.as_pdDataFrame()

	#print("stopping now")
	## stops the stream and returns all the data we've got so far
	market_data2 = app.stop_getting_IB_market_data(tickerid)
	#print(market_data1_as_df)

	## glue the data together
	market_data2_as_df = market_data2.as_pdDataFrame()
	all_market_data_as_df = pd.concat([market_data1_as_df, market_data2_as_df])

	bid_S = str(all_market_data_as_df["bid_size"].mean())
	bid_P = str(all_market_data_as_df["bid_price"].mean())
	ask_S = str(all_market_data_as_df["ask_size"].mean())
	ask_P = str(all_market_data_as_df["ask_price"].mean())
	his_V = str(all_market_data_as_df["historic_vol"].mean())
	impl_V = str(all_market_data_as_df["implied_vol"].mean())
	las_P = str(all_market_data_as_df["last_trade_price"].mean())
	las_S = str(all_market_data_as_df["last_trade_size"].mean())

	IV_CALC = str(all_market_data_as_df["impliedVolatility"].mean())
	DELTA_CALC = str(all_market_data_as_df["delta"].mean())

	app.disconnect()

	return (bid_S, bid_P, ask_S, ask_P, las_S, las_P, his_V, impl_V, IV_CALC, DELTA_CALC)


def work(buys, sells):

	#get transactions that are in date window

	(positions, acc_values, acc_updates, funds) = getAccountInfo()

	bought_transactions = []
	sold_transactions = []


	for buy in buys:
		
		#print("sym: "buy.stock+" type: "+ buy.trade_type+" curr: "+ buy.currency+" exc: "+ buy.exchange+" prim: "+buy.primary_exchange+" exp: "+buy.contract_expiration+" strike: "+buy.strike_price+" cp: "+buy.call_or_put+ " 100 tc:"+ buy.trading_class)

		(bid_S, bid_P, ask_S, ask_P, las_S, las_P, his_V, impl_V, calc_iv, delta) = getData(buy.stock, buy.trade_type, buy.currency, buy.exchange, 
																					buy.primary_exchange, buy.contract_expiration, buy.strike_price, buy.call_or_put, "100", buy.trading_class)

		print("BS: "+ bid_S +" BP: "+ bid_P +" AS: "+ ask_S+" AP: "+ ask_P +" LS: "+ las_S +" LP: "+ las_P +" HV: "+ his_V +" IV: "+ impl_V +" CIV: "+ calc_iv +" DTA: "+ delta)

		##Check for:
		##	Strike price
		##  min - max IV
		##  min max DELTA
		### BID ASK MID???
		price = 0

		if(buy.order_type == "MID"):
			price = (float(bid_P) + float(ask_P))/2
		elif(buy.order_type == "BID"):
			price = float(bid_P)
		elif(buy.order_type == "ASK"):
			price = float(ask_P)

		if(price < 0):
			price = float(las_P)
		
		iv = 0
		if(calc_iv == "nan"):
			iv = float(impl_V)
		else:
			iv = float(calc_iv)

		print("checking for iv: "+ str(iv) + " price: "+ str(price) + " delta: "+ str(delta) + " min delta is: " + buy.min_delta + " max delta is: " + buy.max_delta)

		#(float(buy.buy_price) <=  float(price)) and	
		if((float(buy.min_implied_volatility) < float(iv)) and (float(buy.max_implied_volatility) > float(iv)) and (float(buy.buy_price) <=  float(price))): 	

			if buy.portfolio_percent != "":
				portfolio_value = float(funds)
				money = float(portfolio_value) * float(buy.portfolio_percent) / 100
				
			else:
				money = float(buy.money_allocation)

			quantity = int(money / (price * 100)) ## USE LAST TRADE PRICE
			
			print("bought q: "+ str(quantity) +" at: "+ str(price))
			
			id = transaction(buy.stock, buy.trade_type, buy.currency, buy.exchange, buy.primary_exchange, buy.contract_expiration, 
												"BUY", "MKT", quantity, buy.call_or_put, buy.order_type, buy.strike_price, "100", buy.trading_class)
			
			bought = Bought.query.filter_by(id = buy.id).first()
			bought.status = "Complete"
			bought.money_allocation = quantity #///CHANGE
			bought.buy_price = price
			bought.date_bought = datetime.datetime.now()
			db.session.commit()

			
			if(bought.sold != None):
				sold = Sold.query.filter_by(id = bought.sold.id).first()
				sold.status = "Pending"

			db.session.commit()

			bought_transactions.append(id)


	##########################################################################################################################################################
	##########################################################################################################################################################


	for sell in sells:

		connected_buy = Bought.query.filter_by(id = sell.bought_id).first()

		if(connected_buy is None):
			continue


		(bid_S, bid_P, ask_S, ask_P, las_S, las_P, his_V, impl_V, calc_iv, delta) = getData(connected_buy.stock, connected_buy.trade_type, connected_buy.currency, connected_buy.exchange, 
																					connected_buy.primary_exchange, connected_buy.contract_expiration, connected_buy.strike_price, 
																					connected_buy.call_or_put, "100", connected_buy.trading_class)

		price = 0

		if(sell.order_type == "MID"):
			price = (float(bid_P) + float(ask_P))/2
		elif(sell.order_type == "BID"):
			price = float(bid_P)
		elif(sell.order_type == "ASK"):
			price = float(ask_P)

		if(price < 0):
			price = float(las_P)

		##Check for:
		##	
		##  profit percent??
		## 
		### 
		flag = False

		calculated_profit = (float(price) / float(connected_buy.buy_price)) - 1   

		if(sell.profit_percent == ""):
			if((float(sell.sell_price) >= price)):
				flag = True		
		else:
			if((float(calculated_profit)) >= float(sell.profit_percent)):
				flag = True

		if(flag):	

			#quantity = int(float(sell.quantity) * float(connected_buy.quantity) / 100)
			
			id = transaction(sell.stock, buy.trade_type, buy.currency, buy.exchange, buy.primary_exchange, buy.contract_expiration, 
												"SELL", "MKT", sell.quantity, buy.call_or_put, buy.order_type, buy.strike_price, "100", buy.trading_class)

			sold = Sold.query.filter_by(id = sell.id).first()
			sold.status = "Complete"
			sold.date_sold = datetime.datetime.now()
			db.session.commit()

			sold_transactions.append(id)
			

	return (bought_transactions, sold_transactions)


# uses binary search to minimize the number of API calls
# because every API call takes a while
# saves 5 minutes per function call 

def getValidStrikes(symbol, right, date, min_delta, max_delta):
	
	strikes = []	
	
	## get all contracts with this info 
	## for each 
	## 		get contract data live
	##		check if delta in range
	##		add to list of valids

	(expirationOptions, vals, list_of_cons) = getExpirationDates(symbol, "USD", "SMART", right, "100", date)	

	sortable = [float(i.contract.strike) for i in list_of_cons]
	sortable.sort(reverse = True)	


	if(min_delta != "0" and max_delta !="0"):

		if(float(min_delta) < 0):
			min_delta = str(-float(min_delta))
		if(float(max_delta) > 0):
			max_delta = str(-float(max_delta))

		left = 0
		right = len(sortable)
		
		while(True):
			
			current = int((left + right) / 2) 
			con = sortable[current]
			print(str(current) + " with strike of: " + str(con))

			delta_c = "nan"
			while(delta_c == "nan"):
				(bid_S, bid_P, ask_S, ask_P, las_S, las_P, his_V, impl_V, calc_iv, delta) = getData(symbol, "OPT", "USD", "SMART", 
																					"SMART", date, con, right, "100", "")
				if(float(delta) < 0):
					delta = str(-float(delta))
				delta_c = str(delta)
				print(delta_c)

			
			print(str(delta))

			if(float(delta) < float(min_delta)):
				left = current
				continue

			if(float(delta) > float(max_delta)):
				right = current
				continue

			if(float(delta) > float(min_delta) and float(delta) < float(max_delta)):
				# tu si nabaso, sad prodji cijeli interval
				print("adding: "+ str(con) + " with delta: "+ str(delta))
				strikes.append(float(con))

				index_copy = current
				#lijevo
				while(True):
					index_copy += 1
					con = sortable[index_copy]
						
					delta_c = "nan"
					while(delta_c == "nan"):
						(bid_S, bid_P, ask_S, ask_P, las_S, las_P, his_V, impl_V, calc_iv, delta) = getData(symbol, "OPT", "USD", "SMART", 
																					"SMART", date, con, right, "100", "")
						delta_c = str(delta)
						print(delta_c)

					print("checking: "+ str(con) + " with delta: "+ str(delta))

					if(float(delta) > float(min_delta) and float(delta) < float(max_delta)):
						strikes.append(float(con))
						print("adding: "+ str(con) + " with delta: "+ str(delta))
					else:
						break	



				index_copy = current
				#desno
				while(True):
					index_copy -= 1
					con = sortable[index_copy]
					
					delta_c = "nan"
					while(delta_c == "nan"):
						(bid_S, bid_P, ask_S, ask_P, las_S, las_P, his_V, impl_V, calc_iv, delta) = getData(symbol, "OPT", "USD", "SMART", 
																					"SMART", date, con, right, "100", "")
						delta_c = str(delta)
						print(delta_c)

					print("checking: "+ str(con) + " with delta: "+ str(delta))

					if(float(delta) > float(min_delta) and float(delta) < float(max_delta)):
						strikes.append(float(con))
						print("adding: "+ str(con) + " with delta: "+ str(delta))
					else:
						break


				break
	

	else:
		for con in sortable:
			strikes.append(float(con))

	strikes.sort()
	strikes = [str(i) for i in strikes]

	return strikes





