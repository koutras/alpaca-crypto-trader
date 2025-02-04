from alpaca.data.historical import CryptoHistoricalDataClient
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.data.live import CryptoDataStream
from alpaca.trading.client import TradingClient
import tkinter as tk
from tkinter import ttk
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

from alpaca.trading.requests import (
    LimitOrderRequest,
    GetOrdersRequest,
    GetAssetsRequest
)
from alpaca.data.requests import (
    CryptoBarsRequest
)

from alpaca.trading.enums import (
    AssetClass,
    OrderSide,
    TimeInForce,
    QueryOrderStatus,
    OrderStatus
)

import time as tm
import matplotlib.pyplot as plt
import numpy as np
import datetime
from matplotlib.widgets import Button
import matplotlib.dates as dates
from pymongo import MongoClient
import threading
import json
from bson import Binary

from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler


# set them when the program starts, stream is used for the stream data
# and history for the historic data
stream = None
history = None
account = None
broker = None
api = None
quote_list = []
#taker commision ( this empirically seems to be the value)
comission = 0.021
default_currency = "USD"
coin = ""

# TO DO
# 0) prepei na vrw tropo na afairw ta points needed for a move apo to penalties twn lanes
# 1) dropdown for the currencies - done
# 2) function to gather historic data for up to a year for analysis in df (historic button?)
# 3) show the ability to move up down and expand
# 4) display overlayed ema 12 and ema 16 -> seperate buttons, RSI, MACD, Bollinger bands sounds promissing
# 5) give the ability to stop selling/buying after for example after 10 sells (button with a counter)
# 6) display total balance / balance in sell orders/ balance in buy orders
# 7) cancel active sell/buy order
# 8) create a terminal only version
# 9) separate instances for different coins--> $$$
# 10) find most frequent values in a period --> $$$
# 11) verify that the commision in large euro quantity stands and create a function
# 12) display current price value
# 13) show current order as a horizontal line with color, helpful in case of moving the lanes
# 14) # cancel a active sell order ---> lose x points
# cancel an active buy order ---> 


# dialegeis xroniko diasthma 5-10-15 leptwn
# vriskeis tis poio syxna xrhsimopoioumenew times
# dialegeis thn megalyterh kai thn mikroterh
# dialegeis to meso oro

TEST = True  # when false perform actual order with money
# used to stop program execution
STOP_EXECUTION = False

# todo 
#create a watchlist, alarms etc
# get all historic rates and put them in a db

class LSTM_Model:
    def __init__(self):
        self.model = None
        self.data = None
        self.X = []
        self.y = []
        self.scaler = MinMaxScaler()
        self.close_scaler = None
        self.seq_length = 24
        self.X_train = None
        self.X_test = None
        self.y_train = None
        self.y_test = None
        self.predictions = None
        self.predictions_actual = None
        self.data_scaled = None
        self.test_actual = None

    def normalize_data(self):
        #data_scaled = scaler.fit_transform(data[['close', 'volume', 'MA_12']])
        self.data_scaled = self.scaler.fit_transform(self.data[['close']])
    
    def build_lstm_model(self):
        # Build lstm model

        # disable gpu as I have amd gpu
        import os
        os.environ["CUDA_VISIBLE_DEVICES"] = "-1"  # Disable GPU
        print("X:", self.X[:5], "...")

        # Define the model
        model = Sequential()

        # Add LSTM layers
        model.add(LSTM(units=64, return_sequences=True, input_shape=(self.X.shape[1], self.X.shape[2])))
        model.add(Dropout(0.2))
        model.add(LSTM(units=64, return_sequences=False))
        model.add(Dropout(0.2))

        # Add a Dense output layer
        model.add(Dense(units=1))  # Predicts the next hour's price

        # Compile the model
        model.compile(optimizer='adam', loss='mean_squared_error')
    
    def train_the_model(self):
        # Split data
        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(self.X, self.y, test_size=0.2, shuffle=False)

        # Train the model
        self.model.fit(self.X_train, self.y_train, epochs=50, batch_size=32, validation_data=(self.X_test, self.y_test))
    
    def evaluate_the_model(self):
        # Evaluate the model
        # Make predictions
        predictions = self.model.predict(self.X_test)
        print("X_test:", self.X_test)
        print("Shape of predictions:", predictions.shape)
        print("First few predictions:", predictions[:5])

        # Create a new scaler for the 'Close' price only
        self.close_scaler = MinMaxScaler()
        self.close_scaler.fit(self.data[['close']])  # Fit on the 'Close' column only

        print("close_scaler data min:", self.close_scaler.data_min_)
        print("close_scaler data max:", self.close_scaler.data_max_)

        predictions_actual = self.close_scaler.inverse_transform(predictions)

        dummy_columns = np.zeros((self.y_test.shape[0], 2))  # Add 2 dummy columns
        y_test_with_dummy = np.hstack((self.y_test.reshape(-1, 1), dummy_columns))

        # Inverse transform
        self.y_test_actual = self.scaler.inverse_transform(y_test_with_dummy)[:, 0]  # Extract the first column

        plt.figure(figsize=(10, 6))
        plt.plot(self.y_test_actual, color='blue', label='Actual BTC Price')
        plt.plot(predictions_actual, color='red', label='Predicted BTC Price')
        plt.title('BTC Price Prediction')
        plt.xlabel('Time')
        plt.ylabel('Price')
        plt.legend()
        plt.show()
    
    def make_prediction(self):

        future_steps = 100

        sequence_length = self.seq_length

        # Create an array to hold the future predictions
        future_predictions = []

        # Start with the last sequence of your test data
        last_sequence = self.X_test[-1]

        print("shapes")
        print("shape: ", self.X_test.shape[1])

        for _ in range(future_steps):
            # Reshape the last sequence to match the input shape of the model
            input_sequence = last_sequence.reshape((1, sequence_length, self.X_test.shape[2]))
            
            # Predict the next value
            next_prediction = self.model.predict(input_sequence)
            
            # Append the prediction to the future predictions list
            future_predictions.append(next_prediction[0])
            
            # Update the last sequence to include the new prediction
            last_sequence = np.append(last_sequence[1:], next_prediction, axis=0)

        # Convert future predictions to a numpy array
        future_predictions = np.array(future_predictions)

        # Step 2: Inverse Transform the Predictions
        # Assuming you have a scaler for the 'Close' price
        future_predictions_actual = self.close_scaler.inverse_transform(future_predictions)

        # Step 3: Plot the Results
        # Create a time axis for the future predictions
        future_time = np.arange(len(self.y_test_actual), len(self.y_test_actual) + future_steps)

        plt.figure(figsize=(10, 6))
        plt.plot(self.y_test_actual, color='blue', label='Actual BTC Price')
        plt.plot(future_time, future_predictions_actual, color='green', label='Predicted Future BTC Price')
        plt.title('BTC Price Prediction')
        plt.xlabel('Time')
        plt.ylabel('Price')
        plt.legend()
        plt.show()

    
    def create_data_sequence(self):
        for i in range(len(self.data_scaled) - self.seq_length):
            self.X.append(self.data_scaled[i:i+self.seq_length])
            self.y.append(self.data_scaled[i+self.seq_length, 0])  # Predict the 'Close' price
        return np.array(self.X), np.array(self.y)


    def get_prediction(self, df):
        df.to_csv('btc_min.csv', index=False)
        self.data = pd.read_csv('btc_min.csv')
        self.normalize_data()
        self.create_data_sequence()
        self.build_lstm_model()
        self.train_the_model()
        self.evaluate_the_model()
        self.make_prediction()

class Penalty:
    def initialize(self, corridor):
        # derived values
        self.corridor = corridor
        self.total_penalty_points=0
        self.upper_lane_y = corridor.get_high_y()
        self.lower_lane_y = corridor.get_low_y()
        self.upper_lane_penalty_points = 0 # when current price is above upper
        self.lower_lane_penalty_points = 0 # when current price is below lower penalty
        self.current_median = (self.upper_lane_y + self.lower_lane_y) / 2.0
        self.highest_price = 0
        self.lowest_price = 0
        self.lanes_median = (self.upper_lane_y + self.lower_lane_y) / 2.0
        self.current_price = 0
        self.current_changes= 1
        self.lowest_highest_price_without_loss = (self.lower_lane_y / 0.995) # have to check this
        # values that can be altered
        self.points_needed_for_a_move= 800
        self.upper_lane_penalty_step = 1
        self.lower_lane_penalty_step = 1
        self.grace_step = 100
        self.grace_points = 0
        
    def print(self):
        print("Penalty info")
        print("---------------")
        print("total_penalty_points:",  self.total_penalty_points) 
        print("Points needed for a move: ", self.points_needed_for_a_move - self.total_penalty_points)
        print("upper_lane_penalty_points:",  self.upper_lane_penalty_points)
        print("lower_lane_penalty_points:",  self.lower_lane_penalty_points)
        print("lanes_median:",   self.lanes_median)
        print("current median:", self.current_median)
        print("grace points:", self.grace_points)
        print("---------------\n\n\n")
           
    def increase_grace_points(self):
        self.grace_points = self.grace_points + self.grace_step
        
    def decrease_penalty_upper_lane(self):
        self.upper_lane_penalty_points = self.upper_lane_penalty_points - 2 * self.upper_lane_penalty_step
        
    def decrease_penalty_lower_lane(self):
        self.lower_lane_penalty_points = self.lower_lane_penalty_points - 2 * self.lower_lane_penalty_step

    def increase_penalty_lower_lane(self):
        self.lower_lane_penalty_points = self.lower_lane_penalty_points + self.lower_lane_penalty_step

    def increase_penalty_upper_lane(self):
        self.upper_lane_penalty_points = self.upper_lane_penalty_points + self.upper_lane_penalty_step

    def refresh_penalty_values(self, current_price):
        self.upper_lane_y = self.corridor.get_high_y()
        self.lower_lane_y = self.corridor.get_low_y()
        self.lanes_median = (self.upper_lane_y + self.lower_lane_y) / 2.0
        self.current_median = self.current_median * self.current_changes
        self.current_changes = self.current_changes + 1
        self.current_median = (self.current_median + self.current_price) / float(self.current_changes)
        self.current_price = current_price

        
    def calculate_penalty(self, current_price):
        self.refresh_penalty_values(current_price)
        print ("#####################################################################")
        order = portofolio.fetch_active_order(coin)
       
        # keep track of the lowest and highest prices
        if self.current_price > self.highest_price:
            print("current price > highest price")
            self.highest_price = self.current_price
        
        if self.current_price < self.lowest_price:
            self.lowest_price = self.current_price
            
        # if current price is consistently above upper lane and about to sell, consider increasing lower lane    
        if self.current_price > self.upper_lane_y:
            print("current price over selling price")
            self.increase_penalty_lower_lane()

        # if current price is consistently below lower lane and about to buy, consider decreasing upper lane     
        if self.current_price < self.lower_lane_y:
            print("current price lower that buying price")
            self.increase_penalty_upper_lane()
            
        self.total_penalty_points = self.upper_lane_penalty_points + self.lower_lane_penalty_points - self.grace_points

           
        if (current_price >= self.lower_lane_y and current_price <= self.upper_lane_y): # shrink
        
            while (order and order["side"] == "buy" and  self.lower_lane_penalty_points > 0 and self.lower_lane_y < current_price *0.90):
                print("upping buying price to catch current price")
                corridor.move_lower_lane(1.001)
                self.decrease_penalty_lower_lane()
                order = portofolio.fetch_active_order(coin)
                self.refresh_penalty_values(self.current_price)
                penalty.print()

            while (order and order["side"] == "sell" and  self.upper_lane_penalty_points > 0 and self.lower_lane_y < self.upper_lane_y and self.upper_lane_y > current_price * 1.10):
                print("lowering selling price to catch current price ")
                corridor.move_upper_lane(0.999, current_price)
                self.decrease_penalty_upper_lane()
                order = portofolio.fetch_active_order(coin)
                self.refresh_penalty_values(self.current_price)
                penalty.print()
            print ("#####################################################################")
            return


        if self.total_penalty_points > self.points_needed_for_a_move:
            self.total_penalty_points = self.total_penalty_points - self.points_needed_for_a_move
            percentage = float(self.current_price) / self.lanes_median
            print("dividing:", float(self.current_price), "by ", self.lanes_median)
            self.grace_points = 0
            
            if percentage > 0:
                print("performing a corridor move")
                corridor.move_corridor(percentage, current_price)
                self.upper_lane_penalty_points = 0
                self.lower_lane_penalty_points = 0
              
        print ("#####################################################################")
        
def truncate(f, n):
    '''Truncates/pads a float f to n decimal places without rounding'''
    s = '{}'.format(f)
    if 'e' in s or 'E' in s:
        return '{0:.{1}f}'.format(f, n)
    i, p, d = s.partition('.')
    result =  '.'.join([i, (d+'0'*n)[:n]])
    return float(result)

class Lane:
    # horizontal lane, used by the corridor
    def __init__(self,figure):
        self.axes = figure.axes[0]
        self.ydata = None
        self.reference = None
        self.color = "red"

    def draw(self):
        print("drawing lane y: ", self.ydata)
        self.reference = self.axes.axhline(self.ydata, color=self.color)
        plt.draw()
        
    def get_y(self):
        return self.ydata
    
    def set_y(self,y):
        self.ydata = y
    
    def set_color(self, color):
        self.color = color

    def remove(self):
        self.reference.remove()
        self.reference = None
        plt.draw()      
    
class Corridor:
    def __init__(self, figure):
        self.upperLane = Lane(figure)
        self.lowerLane = Lane(figure)
        self.activeLane= Lane(figure).set_color("green")
        self.figure = figure
        self.axes = figure.axes[0]
        self.cid = None
    
    def draw_active_order(self, order, colour="blue"):
        if order == None:
            return
        self.activeLane.set_y(order.limit_price)
        self.activeLane.draw("green")
        
    def move_upper_lane(self, percentage, current_price, only_upwards = False):
        print(" move upper lane percentage: ", percentage)
        print(" current selling price: ", self.upperLane.get_y())
        new_upper_lane = self.upperLane.get_y() * percentage
        print(" calculated selling price: ", new_upper_lane)
        self.upperLane.remove()
        
        # we must not let upper lane get under lower lane or we lose money
        if(only_upwards):
            new_upper_lane = max([new_upper_lane, self.get_median(), self.upperLane.get_y(), current_price])
            print("trying to increase selling price from ", self.upperLane.get_y(), "to ",new_upper_lane)
            self.upperLane.set_y(new_upper_lane)
        elif new_upper_lane < self.lowerLane.get_y():
            new_upper_lane = self.get_median()
            # make a small correction, change
            while self.lowerLane.get_y() * (1 + comission) >  new_upper_lane:
                new_upper_lane = new_upper_lane * 1 + portofolio.get_asset(coin).min_trade_increment
            print("increasing selling price to be over buying price from", self.upperLane.get_y(), "to ",new_upper_lane)
            self.upperLane.set_y(new_upper_lane)

        else:   
            print("adjusting selling price from", self.upperLane.get_y(), "to ",new_upper_lane)
            self.upperLane.set_y(new_upper_lane)

        
        self.upperLane.draw()
        
    def move_lower_lane(self, percentage, only_downwards=False):
        print(" move lower lane percentage: ", percentage)
        new_lower_lane = self.lowerLane.get_y() * percentage
        self.lowerLane.remove()

        if (only_downwards):
            if percentage < 1:
                print("lowering buying price from", self.lowerLane.get_y(), "to ",new_lower_lane)
                self.lowerLane.set_y(new_lower_lane)
        elif new_lower_lane > self.upperLane.get_y():
            new_lower_lane = self.get_median()
            print("setting buying price to that of median", self.lowerLane.get_y(), "to ",new_lower_lane)
            self.lowerLane.set_y(new_lower_lane)
        else:   
            print("setting buying price from", self.lowerLane.get_y(), "to ",new_lower_lane)
            self.lowerLane.set_y(new_lower_lane)
        self.lowerLane.draw()
        
    def move_corridor(self, percentage, current_price):
        order = portofolio.fetch_active_order(coin)
        print(" move corridor percentage: ", percentage)
        print("selling price", self.upperLane.get_y(), " buying price: ", self.lowerLane.get_y())
        if enable_movement == "y":
            
            if order!=None and order["side"] == "sell":
                self.move_upper_lane(percentage,current_price)
                self.move_lower_lane(percentage, only_downwards = True)
            else:
                self.move_upper_lane(percentage,current_price, only_upwards = True)
                self.move_lower_lane(percentage)
        else:
            print("movement is disabled")
            
    def get_high_y(self):
        return float(self.upperLane.ydata)
    
    def get_low_y(self):
        return float(self.lowerLane.ydata)
    
    def get_median(self):
        return float((self.upperLane.ydata + self.lowerLane.ydata)/2.0)
        
    def draw(self):
        
        # first time draw second time disconnect
        if (self.cid == None):
            self.cid = self.figure.canvas.mpl_connect('button_press_event', self)
            print ("click to set up the lanes and press right click when done")
            
    def __call__(self, event):
        print('click', event)
        
        if  event.button == 3 and self.cid != None:
            self.figure.canvas.mpl_disconnect(self.cid)
            self.cid = None
            return
        
        if event.inaxes == None:
            return

        if self.upperLane.reference == None:
            self.upperLane.ydata = event.ydata
            if self.upperLane.reference != None:
                self.upperLane.remove()
                
            print("setting upper lane to: ", self.upperLane.ydata)
            self.upperLane.draw()
        elif self.lowerLane.reference == None:
            self.lowerLane.ydata = event.ydata
            
            if self.lowerLane.ydata > self.upperLane.ydata:
                (self.lowerLane.ydata, self.upperLane.ydata) =  (self.upperLane.ydata, self.lowerLane.ydata)
            print("setting lower lane to: ", self.lowerLane)
            self.lowerLane.draw()
        else:

            median = self.get_median()
            print("median is: ", median, "lowerLane: ", self.lowerLane.ydata, "upperLane: ",
                  self.lowerLane.ydata)
            if (event.ydata > median):

                self.upperLane.remove()
                self.upperLane.ydata = event.ydata
                # make a small correction, change
                while self.lowerLane.ydata * 1.005 >  self.upperLane.ydata:
                    self.upperLane.ydata = self.upperLane.ydata * 1.002
                self.upperLane.draw()
            else:

                self.lowerLane.remove()
                self.lowerLane.ydata = event.ydata
                # make a small correction, change
                if self.lowerLane.ydata * 1.005 >  self.upperLane.ydata:
                    self.upperLane.ydata = self.upperLane.ydata * 1.002
                    self.upperLane.remove()
                    self.upperLane.draw()
                self.lowerLane.draw()
          
class Point:
    def __init__(self,x=0,y=0, figure= None):
        self.x = x
        self.y = y
        self.figure = figure
        self.axes = figure.axes[0]
        
    def setX(self, x):
        self.x = x

    def setY(self, y):
        self.y = y
            
    def draw(self):
       self.axes.plot([self.x], [self.y] , marker='o', markersize=3, color="red")
       plt.draw()       
        
class Board:
    def __init__(self, figure):
        self.figure = figure
        self.axes = figure.axes[0]
        self.times = []
        self.closing_prices = []
        #cid = self.figure.canvas.mpl_connect('button_press_event', self.onclick)
    
    # for a non historic entry the value is only added if the time is greater that the last added time
    
    def add_entry_in_board(self, closing_price, time, insertAtEnd = False, is_historic_entry = False):
        # if (is_historic_entry):
        #     pass
        # else:
        #     time = time + datetime.timedelta(hours=3)
        latest_added_time  = self.get_latest_time(insertAtEnd)
        print ("latest added time: ", latest_added_time, "about to add time: ", time)
        if(is_historic_entry):
            self.add_to_closing_prices(closing_price, insertAtEnd)
            self.add_to_times(time, insertAtEnd)
        elif latest_added_time==None or latest_added_time < time:
            point = Point(time, closing_price,figure)
            point.draw()
    
    def add_to_closing_prices(self, closing_price, insertAtEnd = False):
        print("adding closing price {0}".format(closing_price))
        if insertAtEnd:
            self.closing_prices.append(closing_price)
        else:
            self.closing_prices.insert(0,closing_price)
        print("Closing price length: ", len(self.closing_prices))

    def add_to_times(self,time, insertAtEnd = False):
  
        print("adding time {0}".format(time))
        if insertAtEnd:
            self.times.append(time)             
        else:
            self.times.insert(0, time)  
        #print("Closing times: ", len(self.times))
        
    def clear_board_values(self):
        self.times.clear()
        self.closing_prices.clear()
        
    def get_latest_time(self,insertAtEnd=False):
        if (len(self.times)):
            if(insertAtEnd):
                return self.times[-1]
            else:
                return self.times[0]
        else:
            return None
        
    def onclick(self, event):
        print("clicked")
        global ix, iy
        ix, iy = event.xdata, event.ydata
        print ("x = %d, y = %f"%(ix, iy))
        global coords
        coords = [ix, iy]
        
    def draw(self):
        self.plotLines(self.times, self.closing_prices)
        plt.draw()
                
    def plotLines(self, x,y):
        self.axes.plot(x, y)     

class Portofolio:
    
    def __init__(self, figure, api):
        self.api = api
        self.figure = figure
        self.rates = {}
        self.assets = {}
        self.axes = self.figure.add_subplot(111, picker = 5)
        self.balance = {}
        self.message_list = []
        self.quote_list = []
        self.df = None
        self.model = None

    def get_message_list(self):
        return self.message_list   

    def add_message(self, message):
        self.message_list.append(message)

    def get_quote_list(self):
        return self.quote_list
    
    def add_quote(self, quote):
        self.quote_list.append(quote)

    def get_current_message(self):
        message = ""
        print ("message list size: ", len(self.message_list))
        
        try: 
            message = self.message_list.pop()
        except:
            pass
        return message
        
    def get_order_winnings(self, order):
        ''' Get Potential Winnings of order'''
        return float(order["qty"]) * float(order["limit_price"])
    
    def fetch_active_order(self, product_id):
        db_order = None
        try:
            for query in [{"symbol":product_id, "status": OrderStatus.NEW}, {"symbol":product_id, "status": OrderStatus.ACCEPTED}]:
                db_order = db_orders.find(query)[0]
                if db_order != None:
                    break
        except Exception as e:
            print(f"An error occurred while fetching active order: {e}")
        return db_order
    
    def delete_all_orders(self):
        db_orders.delete_many({})
    
    def delete_order_from_db(self, order):
        query = {'id':order.id}
        db_orders.delete_one(query)
       
    def insert_or_update_order(self, order):
        query = {'id':order.id}
        old_order = db_orders.find_one(query)
        if old_order != None:
            print ("order exists in database {0}".format(old_order))
            if(old_order["status"] != order.status):
                print ("order {0} has changed status from {1} to {2}".format(order.id, old_order["status"], order.status))
                self.delete_order_from_db(old_order)
                self.handle_order_change(old_order, order)
            # probably the order has been completed (bought)    
            if old_order["side"] == "buy":
                penalty.decrease_penalty_lower_lane()
            else:
                penalty.decrease_penalty_upper_lane()
        else:
            # change key name to make use of it in db
            result =  self.save_order_to_db(order)
            print("inserted order: {0}".format(result))       
        
    def get_position(self, coin):
        # '/' not being supported for position calls
        symbol = coin.replace('/', '')
        self.balance[coin] = 0.0
        try:
            position = api.get_open_position(symbol_or_asset_id=symbol)
            print("position: ", position)
            print("coin: ", position.symbol, "balance:", position.qty)
            self.balance[coin] = position.qty
        except Exception as e:
            print(f"An error occurred while getting balance for coin: {e}")

   
    def fetch_orders(self):
        self.delete_all_orders()
        req = GetOrdersRequest(
            status = QueryOrderStatus.ALL,
            symbols = [coin]
        )
        orders = api.get_orders(req)
        active_order = self.fetch_active_order(coin)
        if active_order != None:
            corridor.draw_active_order(active_order)

        for order in orders:
            print ("order is: ", order)
            if order.status == OrderStatus.FILLED and active_order != None:
                pass
            # track open orders in the db
            elif order.status == OrderStatus.ACCEPTED or order.status == OrderStatus.NEW or active_order == None:
                self.insert_or_update_order(order)
            
    def handle_order_change(self,  old_order, new_order):
       # balance has changed, refresh
       self.refresh_portofolio_and_orders()
       cash_balance = self.get_cash_balance()
       if new_order["status"] == OrderStatus.FILLED:
           if old_order["status"] in [OrderStatus.NEW, OrderStatus.PENDING_NEW]:
               # old order is no more needed
               self.delete_order_from_db(old_order)
               if old_order["side"] == "buy":
                   print(" Bought; placing a sell order")
                   if (cash_balance > 1):
                       self.issue_sell_order(new_order["symbol"], corridor.get_high_y())
                      

               elif old_order.side =="sell":
                   print("sold")
                   penalty.increase_grace_points()
                   print(" Bought; placing a buy order")
                   self.issue_buy_order(new_order.product_id, corridor.get_low_y())
               # old order is of no use in the db
               else:
                   print("unknown error in order side")
                
    def get_open_orders_for_coin_from_db(self, coin):
        orders = []
        try:
            query = {"symbol": coin, "status": OrderStatus.NEW }
            orders = db_orders.find(query)
        except Exception as e:
            print(f"An error occurred fetching a db order: {e}")
        return list(orders)
    
    def get_side_orders_for_coin_from_db(self, coin, side):
        orders = []
        try:
            query = {"symbol": coin, "status": OrderStatus.NEW, "side":side }
            orders = db_orders.find(query)
            print ("retrieved db orders: ", orders, "side:", side)
        except:
            pass
        return list(orders)
    
    def get_buy_orders_for_coin_from_db(self, coin):
        return self.get_side_orders_for_coin_from_db(coin,"buy")  
    
    def get_sell_orders_for_coin_from_db(self, coin):
        return self.get_side_orders_for_coin_from_db(coin,"sell")
                                                      
    def get_cash_balance(self):
        return float(self.balance[default_currency])

    def get_coin_balance(self, coin):
        return float(self.balance[coin])
    
    def save_order_to_db(self, order):
        order_data = {
            'id': order.id,
            'symbol': order.symbol,
            'qty': order.qty,
            'side': order.side,
            'type': order.type,
            'time_in_force': order.time_in_force,
            'status': order.status,
            'filled_qty': order.filled_qty,
            'created_at': order.created_at,
            'updated_at': order.updated_at,
            'limit_price': order.limit_price,
            
        }
        result = db_orders.insert_one(order_data)
        return result.inserted_id
    

    def issue_buy_order(self, product_id,  price, size = 0.0):
        cash_balance = self.get_cash_balance()
        print("cash balance:", cash_balance )
        
        if (price > 1000): #avoid truncating prices of very small coins
            price = truncate(price,1)
            print("truncate price to: ", price)
        elif (price > 100):
            price = truncate(price,2)
            print("truncate price to: ", price)

        if size==0.0:
            size = (cash_balance / float(price)) * (1 - float(comission))
            size = truncate(size,4)
            print("truncate size to: ", size)
        asset = portofolio.get_asset(product_id)
        # here I can do sth better than a simple truncation

        if float(size) < float(asset.min_order_size):
            print("size is considered too small for alpaca, skipping to avoid penalties")
            return
            
        if float(size) > 1000.0:
            size = truncate(size, 0)
        print ("issuing for buying: ", product_id, "size: ", size, "at price: ", price)
#min hour day
        
        market_order_data = LimitOrderRequest(
                    symbol=product_id,
                    qty=size,
                    side=OrderSide.BUY,
                    time_in_force=TimeInForce.GTC,
                    limit_price = price
        )
        market_order=None
        try:
            market_order = api.submit_order(
                order_data=market_order_data
            )

        except Exception as e:
            print(f"An error occurred while performing a buy order: {e}")

        if market_order!=None:
            portofolio.save_order_to_db(market_order)

        print("result of order: {0}".format(market_order))

            
    def issue_sell_order(self, product_id,  price, size = ""):
        if size=="":
            how_much = "all"
        else:
            how_much = size
        print ("issuing for selling: ", product_id, "size: ", how_much, "at price: ", price)

        if price > 1.0 : #avoid truncating prices of very small coins
            price = truncate(price,2)        
        
        if size=="":
            size = self.get_coin_balance(product_id)
            # price = truncate(price,3)
            # size = truncate(size,3)
            asset = portofolio.get_asset(product_id)
            # here I can do sth better than a simple truncation
            print ("maximum order size to be", size)
            if size < float(asset.min_order_size):
                print("size is considered too small for alpaca, skipping to avoid penalties")
                return
            market_order_data = LimitOrderRequest(
                      symbol=product_id,
                      qty=size,
                      side=OrderSide.SELL,
                      time_in_force=TimeInForce.GTC,
                      limit_price = price
            )
            market_order=None
            try:
                market_order = api.submit_order(
                    order_data=market_order_data
                )
            except Exception as e:
                print(f"An error occurred while performing a sell order: {e}")

            print("result of order: {0}".format(market_order))
            if market_order!=None:
                portofolio.save_order_to_db(market_order)
            
    def get_nth_day_before_today_historic_rates(self, coin, n):
        pastTime = datetime.datetime.now() - datetime.timedelta(days = n)
        pastTime = pastTime.isoformat()
        current_time =datetime.datetime.now().isoformat()
        print("past time is: ", pastTime)
        request_params = CryptoBarsRequest(
                        symbol_or_symbols=[coin],
                        timeframe=TimeFrame.Day,
                        start=pastTime,
                        end=current_time
                 )

    def get_historic_last_days(self, coin , n):
        for i in range (1, n):
            data = self.get_nth_day_before_today_historic_rates(coin,i)
            for line in data:
               epoc_time, low, high, open, close, volume = line
               query = {'_id':epoc_time}
               found_tick = db_ticks.find_one(query)
               if found_tick != None:
                   line["_id"] = epoc_time
                   db_ticks.insert_one(line)
               else:
                   print("tick exists in database, omitting")
                

        print ("Coin: {0} rates: {1}".format(coin, self.rates[coin]))
# takes insufficient funds
    def get_historic_rates(self, coin, hoursBefore = 100):
        pastTime = datetime.datetime.now() - datetime.timedelta(hours=hoursBefore)
        self.pastTime = pastTime
        pastTime = pastTime.isoformat()
        print("past time is: ", pastTime)
        # no keys required for crypto data

        request_params = CryptoBarsRequest(
                        symbol_or_symbols=[coin],
                        timeframe=TimeFrame.Minute,
                        start=pastTime
                 )
        
        bars = history.get_crypto_bars(request_params)
        
        print ("Historic data received {0}", bars)
        print( "turned to df {0}", bars.df)
        self.df = bars.df
        # have to get the rates here
        self.rates[coin] = bars[coin]
        print ("Coin: {0} rates: {1}".format(coin, self.rates[coin]))
    
    def draw_historic_rates(self, coin):
        closing_prices = []
        times = []
        for line in self.rates[coin]:
            board.add_entry_in_board(line.close, line.timestamp, is_historic_entry = True)
                
        print("closing prices size: ", len(closing_prices), "times size: ", len(times))
        self.axes.xaxis.set_major_formatter(dates.DateFormatter("%d-%m %H:%M"))
        board.draw()

    def get_cash_balance(self):
        # assuming that we trade only currencies with usd
        print("getting cash balance")
        account = api.get_account()
        balance = 0.0
        if float(account.cash) > 0:
            balance = float(account.cash)               
            if balance > 0.0:
                print("account: ", balance , "currency:", account.currency)
            self.balance[account.currency] = balance
        print("cash balance is: ", self.balance)
        return balance

    def api_get_assets(self):
        # not sure what this does
        search_params = GetAssetsRequest(asset_class=AssetClass.CRYPTO)
        assets = api.get_all_assets(search_params)
        for asset in assets:
            self.assets[asset.symbol] = asset
            print("asset: ", asset)
        return assets

    def get_asset(self, symbol):
        return self.assets[symbol]

    def refresh_portofolio_and_orders(self):
        self.get_cash_balance()
        self.fetch_orders()

def handler(*args, **kwargs):
    print('drawing corridor')
    corridor.draw()

def stop_execution(*args, **kwargs):
    global STOP_EXECUTION
    STOP_EXECUTION = True
    stream.close()

def start(*args, **kwargs):
    global STOP_EXECUTION
    STOP_EXECUTION = False
    print("starting the websocket, good luck!!")
    penalty.initialize(corridor)
    
    while (STOP_EXECUTION == False):
        
        current_message =  portofolio.get_current_message()
        print ("\ncurrent message ",current_message)
        
        if current_message == "":
             print(".... no new messages ....")
             tm.sleep(10)
             continue
         
        print("resuming...")
        portofolio.refresh_portofolio_and_orders()
        
        print("type: ", type(current_message))
        print ("current message: ", current_message)
        coin = current_message.symbol
        price = float(current_message.close)
        print("current price: ", price)

        current_timestamp = current_message.timestamp
        print("try adding ({0}, {1})".format(current_timestamp,price))
        board.add_entry_in_board(price, current_timestamp,  insertAtEnd = False)
        
        cash_balance = portofolio.get_cash_balance()
        print("current cash balance: ", cash_balance)
        
        current_price = float(current_message.close)
        penalty.calculate_penalty(current_price)
        penalty.print()
        print( current_message.symbol, " is now: ", current_price  )
        current_worth = 0.0
        estimated_order_worth = 0.0
        current_worth = current_worth + portofolio.get_coin_balance(coin) * current_price
        
        sell_orders = portofolio.get_sell_orders_for_coin_from_db(coin)
        buy_orders = portofolio.get_buy_orders_for_coin_from_db(coin)
        # an asset is basically limits for a coin, min order, lowest price increment
        asset = portofolio.get_asset(coin)
        
        if len(sell_orders):
            for order in sell_orders:
                print("Active Sell order:", order)
                estimated_order_worth = estimated_order_worth + portofolio.get_order_winnings(order)     
                print("order with status: ", order["status"], "actual worth: ", current_worth, " estimated_worth ", estimated_order_worth )
        else:
            if portofolio.get_coin_balance(current_message.symbol) > asset.min_order_size:
                portofolio.issue_sell_order(current_message.symbol, corridor.get_high_y())
                
        if len(buy_orders):
            for order in buy_orders:
                cash_balance = cash_balance - float(order["price"]) * float(order["size"])

        print("available cash balance after substructing balance reserved for buy orders: ", cash_balance)
        # dont let cash balance inactive, will have to find a more clever way eventually
        if cash_balance > 1.0:
            portofolio.issue_buy_order(current_message.symbol, corridor.get_low_y())

        print("estimated sell order worth {0} current order worth {1}".format(estimated_order_worth, current_worth))
        
        current_portofolio_worth = current_worth + cash_balance
        print ("actual portofolio worth {0}".format(current_portofolio_worth))        
                
        if current_price > (corridor.get_high_y() + corridor.get_low_y())/2 :
            print("price is above the middle")
            sell_orders = portofolio.get_sell_orders_for_coin_from_db(coin)
            if len(sell_orders) == 0 and portofolio.get_coin_balance(current_message.symbol) > 0.0:
                print("Price above median lane but no active sell orders; issuing sell order and passing")
                # there is balance in that coin
                if portofolio.get_coin_balance(current_message.symbol) > 0.0: 
                    portofolio.issue_sell_order(current_message.symbol, corridor.get_high_y())
                else:
                    print("cannot issue a sell order since there isn't any balance for this coin")
                    
                continue
         
            # hurray about to sell/ sold
            if current_price >= corridor.get_high_y():
                # fetch orders when refreshing the portofolio will discover if an
                # order has been completed and trigger a new one
                portofolio.refresh_portofolio_and_orders()

        else:
            print("price is below the middle")
            buy_orders = portofolio.get_buy_orders_for_coin_from_db(coin)
            if len(buy_orders) == 0:
                print("Price below median lane but no active buy orders; buying and passing")
                portofolio.issue_buy_order(current_message.symbol, corridor.get_low_y())

                continue
            print("effective buy orders: ")
            if current_price <= corridor.get_low_y():
                portofolio.refresh_portofolio_and_orders()
            for order in buy_orders:
                print(order)

def start_main_loop(*args, **kwargs):
    thread = threading.Thread(target=start)
    thread.start()   

async def get_rates(*args, **kwargs):
    portofolio.get_historic_last_days(coin,365)
    
# Load credentials from a file
with open('credentials_live.json') as f:
    creds_live = json.load(f)
with open('credentials_paper.json') as f:
    creds_paper = json.load(f)
with open('credentials_broker_paper.json') as f:
    creds_broker_paper = json.load(f)            

API_KEY_LIVE = creds_live['API_KEY']
API_SECRET_LIVE = creds_live['API_SECRET']

API_KEY_PAPER = creds_paper['API_KEY']
API_SECRET_PAPER = creds_paper['API_SECRET']

API_BROKER_KEY_PAPER = creds_broker_paper['API_KEY']
API_BROKER_SECRET_PAPER = creds_broker_paper['API_SECRET']

BASE_URL = 'https://paper-api.alpaca.markets'  # Use 'https://api.alpaca.markets' for live trading


history = CryptoHistoricalDataClient(API_KEY_LIVE, API_SECRET_LIVE)
stream = CryptoDataStream(API_KEY_PAPER, API_SECRET_PAPER)
# will have to see if the paper api_key works
# set this via global variable on top
if TEST:
    api = TradingClient(API_KEY_PAPER, API_SECRET_PAPER)

else:
    api = TradingClient(API_KEY_LIVE, API_SECRET_LIVE, paper=False)
    #stream = CryptoDataStream(API_KEY_LIVE, API_SECRET_LIVE)

# initiate database
mongo_client = MongoClient('mongodb://localhost:27017/?uuidRepresentation=standard')

db = mongo_client.cryptocurrency_database

db_orders = db["orders"]

# all the elements will need the figure
figure = plt.figure(figsize=(8,6))

portofolio = Portofolio(figure, api)

corridor  = Corridor(figure)
penalty = Penalty()
board = Board(figure)

async def on_bar(data):
    portofolio.add_message(data)
    print(f"Bar data: {data}")

async def on_quote(data):
    portofolio.add_quote(data)
    print(f"Quote: {data}")

# Subscribe to bar data for the specified cryptocurrency
stream.subscribe_bars(on_bar, coin)
# leave this for now until we can use it
#stream.subscribe_quotes(on_quote, coin)


# get different coins, store minimum order size etc
assets = portofolio.api_get_assets()
coins = []
for asset in assets:
    coins.append(asset.symbol)
coins.sort()
# Create the main window
root = tk.Tk()
root.title("Select Coin")

# Create a StringVar to hold the selected coin
selected_coin = tk.StringVar()

# Create the dropdown menu
dropdown = ttk.Combobox(root, textvariable=selected_coin, values=coins)
dropdown.grid(column=0, row=0)
dropdown.current(0)  # Set default selection

coin = ""
# Function to handle selection
def on_select(event):
    global coin
    coin = selected_coin.get()
    print("coin is: ", coin)
    db_ticks = db[coin]
    root.quit()  # Close the GUI window

while coin not in coins:
    # Bind the selection event
    dropdown.bind("<<ComboboxSelected>>", on_select)
    # Run the GUI event loop
    root.mainloop()
    print("coin selected: ", coin)   
    #coin = input("Give input coin: ") or "BTC/USD"

db_ticks = db[coin]

enable_movement = "n"
#enable_movement = input ("enable movement (use it at your own risk) (y/n) ?: ")

portofolio.get_historic_rates(coin)
model = LSTM_Model()
model.get_prediction(portofolio.df)

portofolio.draw_historic_rates(coin)
# get the current balance in USD
portofolio.get_cash_balance()
portofolio.get_position(coin)
corridor.draw_active_order(portofolio.fetch_active_order(coin))

print ("balance on this coin is: ", portofolio.get_coin_balance(coin))
portofolio.fetch_orders()

thread = threading.Thread(target=stream.run)
thread.start()

axstart = plt.axes([0, 0, 0.1, 0.075])
axhello = plt.axes([0.1, 0, 0.1, 0.075])
axstop = plt.axes([0.2, 0, 0.1, 0.075])
axhistoric_rates = plt.axes([0.5, 0, 0.1, 0.075])

bstart = Button(axstart, 'Start')
bhello = Button(axhello, 'Lanes')
bstop = Button(axstop, 'Stop')
bhistoric = Button(axhistoric_rates, 'Historic')

bhello.on_clicked(handler)
bstart.on_clicked(start_main_loop)
bstop.on_clicked(stop_execution)
bhistoric.on_clicked(get_rates)

plt.show()
