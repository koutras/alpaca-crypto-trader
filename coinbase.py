import cbpro, json
import time as tm
from cbpro.cbpro_auth import get_auth_headers
import matplotlib.pyplot as plt
import numpy as np
import datetime
from websocket import create_connection, WebSocketConnectionClosedException
from matplotlib.widgets import Button
import matplotlib.dates as dates
from pymongo import MongoClient
import threading
import ast



# TO DO
# 0) prepei na vrw tropo na afairw ta points needed for a move apo to penalties twn lanes
# 1) dropdown for the currencies
# 2) function to gather historic data for up to a year for analysis
# 3) show the ability to move up down and expand
# 4) display overlayed ema 12 and ema 16
# 5) give the ability to stop selling/buying after for example after 10 sells
# 6) display total balance / balance in sell orders/ balance in buy orders
# 7) cancel active sell/buy order
# 8) create a terminal only version
# 9) separate instances for different coins
# 10) find most frequent values in a period
# 11) verify that the commision in large euro quantity stands and create a function
# 12) display current price value
# 13) show current order as a horizontal line with color

# possible input /


# dialegeis xroniko diasthma 5-10-15 leptwn
# vriskeis tis poio syxna xrhsimopoioumenew times
# dialegeis thn megalyterh kai thn mikroterh
# dialegeis to meso oro

# fees after every order completed  ~0.0035%

TEST = False  # when false perform actual order with money
# used to stop program execution
STOP_EXECUTION = False


# todo 
#create a watchlist, alarms etc
# get all historic rates and put them in a db


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
        self.points_needed_for_a_move= 25
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
            
        if self.current_price > self.upper_lane_y and order!=None and order["side"] == "buy":
            print("current price over selling price and active buy order")
            self.upper_lane_penalty_points = self.upper_lane_penalty_points + self.upper_lane_penalty_step

        if self.current_price > self.lower_lane_y and order!=None and order["side"] == "buy":
            print("current price over buying price")
            self.increase_penalty_lower_lane()
            
        if self.current_price < self.lower_lane_y and order!=None and order["side"] == "sell":
            print("current price lower that buying price")
            self.increase_penalty_lower_lane()
            
        if self.current_price > self.lanes_median and order!=None and order["side"] == "buy":
            print("current price very high for a buy order")
            self.increase_penalty_lower_lane()
            
        if self.current_price < self.lanes_median and order!=None and order["side"] == "sell":
            print("current price very low for a sell order")
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
   
            
        
        
    
        
#class Move:
#    def move_upper_

def truncate(f, n):
    '''Truncates/pads a float f to n decimal places without rounding'''
    s = '{}'.format(f)
    if 'e' in s or 'E' in s:
        return '{0:.{1}f}'.format(f, n)
    i, p, d = s.partition('.')
    return '.'.join([i, (d+'0'*n)[:n]])


class myWebsocketClient(cbpro.WebsocketClient):
        
    def on_open(self):
        print("opening socket")
        self.url = "wss://ws-feed.pro.coinbase.com/"
        self.products = [coin]
        self.message_list = []
        
        print("Lets count the messages!")
    def on_message(self, msg):
        print(json.dumps(msg, indent=4, sort_keys=True))
        self.current_message = msg
        if 'price' in msg and 'type' in msg:
            print ("Message type:", msg["type"],
                   "\t@ {:.3f}".format(float(msg["price"])))
            self.message_list.append(msg)

        print ("message list size: ", len(self.message_list))

    def get_current_message(self):
        message = ""
        print ("message list size: ", len(self.message_list))
        
        try: 
            message = self.message_list.pop()
        except:
            pass
        return message
             
    def get_message_list(self):
        return self.message_list
    
    def on_close(self):
        print("-- Goodbye! --")
        tm.sleep(5)
        print ("Reconnecting ...")
        self._connect()
        tm.sleep(3)
        self.start()
    def _connect(self):
        print ("calling connect")
        if self.products is None:
            self.products = [coin]
        elif not isinstance(self.products, list):
            self.products = [self.products]
    
        if self.url[-1] == "/":
            self.url = self.url[:-1]
    
        if self.channels is None:
            self.channels = [{"name": "ticker", "product_ids": [product_id for product_id in self.products]}]
            sub_params = {'type': 'subscribe', 'product_ids': self.products, 'channels': self.channels}
        else:
            sub_params = {'type': 'subscribe', 'product_ids': self.products, 'channels': self.channels}
    
        if self.auth:
            timestamp = str(tm.time())
            message = timestamp + 'GET' + '/users/self/verify'
            auth_headers = get_auth_headers(timestamp, message, self.api_key, self.api_secret, self.api_passphrase)
            sub_params['signature'] = auth_headers['CB-ACCESS-SIGN']
            sub_params['key'] = auth_headers['CB-ACCESS-KEY']
            sub_params['passphrase'] = auth_headers['CB-ACCESS-PASSPHRASE']
            sub_params['timestamp'] = auth_headers['CB-ACCESS-TIMESTAMP']
    
        self.ws = create_connection(self.url)   
        self.ws.send(json.dumps(sub_params))


class Lane:
    # horizontal lane, used by the corridor
    def __init__(self,figure):
        self.axes = figure.axes[0]
        self.ydata = None
        self.reference = None

    def draw(self):
        print("drawing lane y: ", self.ydata)
        self.reference = self.axes.axhline(self.ydata, color="red")
        plt.draw()
        
    def get_y(self):
        return self.ydata
    
    def set_y(self,y):
        self.ydata = y

    def remove(self):
        self.axes.lines.remove(self.reference)
        self.reference = None
        plt.draw()
        
    

class Corridor:
    def __init__(self, figure):
        self.upperLane = Lane(figure)
        self.lowerLane = Lane(figure)
        self.figure = figure
        self.axes = figure.axes[0]
        self.cid = None
        
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
            while self.lowerLane.get_y() * 1.005 >  new_upper_lane:
                new_upper_lane = new_upper_lane * 1.002
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
        return self.upperLane.ydata
    
    def get_low_y(self):
        return self.lowerLane.ydata
    
    def get_median(self):
        return (self.upperLane.ydata + self.lowerLane.ydata)/2.0
        
    def draw(self):
        
        # first time draw second time disconnect
        if (self.cid == None):
            self.cid = self.figure.canvas.mpl_connect('button_press_event', self)
            print ("click to set up the lanes and press right click when done")


# cancel a active sell order ---> lose x points
# cancel an active buy order ---> 
            
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
        if (is_historic_entry):
            pass
        else:
            time = time + datetime.timedelta(hours=3)
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
            self.closing_prices.pop(0)
            self.closing_prices.append(closing_price)
        else:
            self.closing_prices.insert(0,closing_price)
        #print("Closing price length: ", len(self.closing_prices))

    def add_to_times(self,time, insertAtEnd = False):

  
        print("adding time {0}".format(time))
        if insertAtEnd:
            self.times.pop(0)
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
    
    def __init__(self, figure):
        self.figure = figure
        self.rates = {}
        self.axes = self.figure.add_subplot(111, picker = 5)
        self.balance = {}
        
    def get_order_winnings(self, order):
        ''' Get Potential Winnings of order'''
        return float(order["size"]) * float(order["price"])
    
    def fetch_order(self, id):
        order = auth_client.get_order(id)
        return order
    
    def fetch_active_order(self, product_id):
        db_order = None
        try:
            query = {"product_id":coin, "status": "open"}
            db_order = db_orders.find(query)[0]   
        except:
            pass
        #order = self.fetch_order(db_order.id)
        return db_order
    
    def delete_all_orders(self):
        db_orders.delete_many({})
    
    def delete_order_from_db(self,order):
        query = {'_id':order["id"]}
        db_orders.delete_one(query)
       
    
    def insert_or_update_order(self, order):
        query = {'_id':order["id"]}
        old_order = db_orders.find_one(query)
        if old_order != None:
            print ("order exists in database {0}".format(old_order))
            if(old_order["status"] != order["status"]):
                print ("order {0} has changed status from {1} to {2}".format(order["_id"], old_order["status"], order["status"]))
                self.delete_order_from_db(old_order)
                self.handle_order_change(old_order, order)
            if old_order["side"] == "buy":
                penalty.decrease_penalty_lower_lane()
            else:
                penalty.decrease_penalty_upper_lane()

                
        else:
            # change key name to make use of it in db
            order["_id"] = order.pop("id")
            result = db_orders.insert_one(order)
            print("inserted order: {0}".format(result.inserted_id))
        
        
    
    def fetch_orders(self):
        self.delete_all_orders()
        orders = list(auth_client.get_orders())  
        for order in orders:
            print ("order is: ", order)
            self.insert_or_update_order(order)

            
    def handle_order_change(self,  old_order, new_order):
       # balance has changed, refresh
       self.refresh_portofolio_and_orders()
       cash_balance = self.get_cash_balance()
       if new_order["status"] == "closed":
           if old_order["status"] == "open":
               # old order is no more needed
               self.delete_order_from_db(old_order)
               if old_order["side"] == "buy":
                   print(" Bought; placing a sell order")
                   if (cash_balance > 1):
                       self.issue_sell_order(new_order["product_id"], corridor.get_high_y())
                      

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
            query = {"product_id": coin, "status": "open" }
            orders = db_orders.find(query)
        except:
            pass
        return list(orders)
    
    def get_side_orders_for_coin_from_db(self, coin, side):
        orders = []
        try:
            query = {"product_id": coin, "status": "open", "side":side }
            orders = db_orders.find(query)
        except:
            pass
        return list(orders)
    
    def get_buy_orders_for_coin_from_db(self, coin):
        return self.get_side_orders_for_coin_from_db(coin,"buy")
    
    
    def get_sell_orders_for_coin_from_db(self, coin):
        return self.get_side_orders_for_coin_from_db(coin,"sell")
                           
                           
    def get_cash_balance(self):
        return self.balance["EUR"]

        
    def get_coin_balance(self, coin):
            return float(self.balance[coin])
             
             
    def issue_buy_order(self, product_id,  price, size = "", test = TEST):
        
        cash_balance = self.get_cash_balance()
        print("cash balance:", )
        
        if size=="":
            size = (cash_balance * 0.995) / price
            print ("maximum size calculated to be", size)
            
        if size < 0.01:
            print("size is considered too small for coinbase, skipping to avoid penalties")
            return
        if price > 1.0 : #avoid truncating prices of very small coins
            price = truncate(price,2)
 
        size = truncate(size,1)
        if float(size) > 1000.0:
            size = truncate(size, 0)
        print ("issuing for buying: ", product_id, "size: ", size, "at price: ", price)
#min hour day
        if test == False:
            result = auth_client.buy(price=price, 
                    size=size, 
                    order_type='limit',
                    product_id=product_id,time_in_force="GTT", cancel_after="day")
            print("result of order: {0}".format(result))

            
    def issue_sell_order(self, product_id,  price, size = "", test = TEST):
        print ("issuing for selling: ", product_id, "size: ", size, "at price: ", price)

        if price > 1.0 : #avoid truncating prices of very small coins
            price = truncate(price,2)        
        
        if size=="":
            size = self.get_coin_balance(coin)
            price = truncate(price,3)
            size = truncate(size,3)
            print ("maximum order size to be", size)
        if test == False:
            result = auth_client.sell(price=price, 
                size=size, 
                order_type='limit',
                product_id=product_id)
            print("result of order: {0}".format(result))
            


    

    def get_nth_day_before_today_historic_rates(self, coin, n):
        pastTime = datetime.datetime.now() - datetime.timedelta(days = n)
        pastTime = pastTime.isoformat()
        current_time =datetime.datetime.now().isoformat()
        print("past time is: ", pastTime)
        rates = auth_client.get_product_historic_rates(product_id = coin, start = pastTime, end = current_time, granularity = 21600 )
        self.rates = rates
        print("rates received")
        print("----------------")
        print(rates)
        return rates

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
    def get_historic_rates(self, coin, hoursBefore = 40):
        pastTime = datetime.datetime.now() - datetime.timedelta(hours=hoursBefore)
        self.pastTime = pastTime
        pastTime = pastTime.isoformat()
        current_time =datetime.datetime.now().isoformat()
        print("past time is: ", pastTime)
        self.rates[coin] = auth_client.get_product_historic_rates(product_id = coin, start = pastTime, end = current_time, granularity = 900)

        print ("Coin: {0} rates: {1}".format(coin, self.rates[coin]))

    def draw_historic_rates(self, coin):
        closing_prices = []
        times = []
        for line in self.rates[coin]:
            epoc_time, low, high, open, close, volume = line            
            midnight = datetime.datetime.combine(datetime.datetime.today(), datetime.time.min) 
            yesterday_midnight = midnight - datetime.timedelta(days=3)
            if  datetime.datetime.fromtimestamp(epoc_time) > yesterday_midnight :
                dt =  datetime.datetime.fromtimestamp(epoc_time)
                board.add_entry_in_board(close, dt, is_historic_entry = True)
                
        print("closing prices size: ", len(closing_prices), "times size: ", len(times))
        self.axes.xaxis.set_major_formatter(dates.DateFormatter("%d-%m %H:%M"))
        board.draw()

    def get_balances(self):
        # assuming that we trade only currencies with euro
        accounts = auth_client.get_accounts()
        postfix = "-EUR"

        for account in accounts:
            if "EUR" in account['currency']:
                postfix = ""
            else:
                postfix = "-EUR"
            balance = 0.0
            if float(account['balance']) > 0:
                balance = float(account['balance'])
                
            self.balance[account['currency']+postfix] = balance
            if balance > 0.0:
                print("account: ", account["currency"], "balance: ", balance)
        print("cash balance is: ", self.balance['EUR'])

    def refresh_portofolio_and_orders(self):
        self.get_balances()
        self.fetch_orders()

def handler(*args, **kwargs):
    print('drawing corridor')
    corridor.draw()

def stop_execution(*args, **kwargs):
    global STOP_EXECUTION
    STOP_EXECUTION = True
    wsClient.close()

def start(*args, **kwargs):
    global STOP_EXECUTION
    STOP_EXECUTION = False
    wsClient.start()
   # board.clear_board_values()
    
    penalty.initialize(corridor)
    
    print(wsClient.url, wsClient.products)
    while (STOP_EXECUTION == False):
        
        current_message =  wsClient.get_current_message()
        #print ("\ncurrent message ",current_message)

        
        if current_message == "":
             print(".... no new messages ....")
             tm.sleep(10)
             continue
         
        print("resuming...")
        portofolio.refresh_portofolio_and_orders()
        
        print("type: ", type(current_message))
        #print ("current message: ", current_message)
        coin = current_message["product_id"]
        price = float(current_message["price"])
        print("current price: ", price)


        # lets hope this works
        timestamp = datetime.datetime.strptime(current_message["time"], '%Y-%m-%dT%H:%M:%S.%fZ').timestamp()
        fmt_time =  datetime.datetime.fromtimestamp(timestamp)

        print("try adding ({0}, {1})".format(fmt_time,price))
        board.add_entry_in_board(price, fmt_time,  insertAtEnd = True)
        
        cash_balance = portofolio.get_cash_balance()
        print("current cash balance: ", cash_balance)
        
        current_price = float(current_message["price"])
        penalty.calculate_penalty(current_price)
        penalty.print()
        print( current_message["product_id"], " is now: ", current_price  )
        current_worth = 0.0
        estimated_order_worth = 0.0
        current_worth = current_worth + portofolio.get_coin_balance(coin) * current_price
        
        sell_orders = portofolio.get_sell_orders_for_coin_from_db(coin)
        buy_orders = portofolio.get_buy_orders_for_coin_from_db(coin)

        
        if len(sell_orders):
            for order in sell_orders:
                print("Active Sell order:", order)
                estimated_order_worth = estimated_order_worth + portofolio.get_order_winnings(order)     
                print("order with status: ", order["status"], "actual worth: ", current_worth, " estimated_worth ", estimated_order_worth )
        else:
            if portofolio.get_coin_balance(current_message["product_id"]) > 0.0:
                portofolio.issue_sell_order(current_message["product_id"], corridor.get_high_y())
                
    
        if len(buy_orders):
            for order in buy_orders:
                cash_balance = cash_balance - float(order["price"]) * float(order["size"])

        print("available cash balance after substructing balance reserved for buy orders: ", cash_balance)
        # dont let cash balance inactive, will have to find a more clever way eventually
        if cash_balance > 1.0:
            portofolio.issue_buy_order(current_message["product_id"], corridor.get_low_y())

         
        print("estimated sell order worth {0} current order worth {1}".format(estimated_order_worth, current_worth))
        
        current_portofolio_worth = current_worth + cash_balance
        print ("actual portofolio worth {0}".format(current_portofolio_worth))        
        
        
        if current_price > (corridor.get_high_y() + corridor.get_low_y())/2 :
            print("price is above the middle")
            sell_orders = portofolio.get_sell_orders_for_coin_from_db(coin)
            if len(sell_orders) == 0:
                print("Price above median lane but no active sell orders; issuing sell order and passing")
                # there is balance in that coin
                if portofolio.get_coin_balance(current_message["product_id"]) > 0.0: 
                    portofolio.issue_sell_order(current_message["product_id"], corridor.get_high_y())
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
                portofolio.issue_buy_order(current_message["product_id"], corridor.get_low_y())

                continue
            print("effective buy orders: ")
            if current_price <= corridor.get_low_y():
                portofolio.refresh_portofolio_and_orders()
            for order in buy_orders:
                print(order)
            
        
def start_thread(*args, **kwargs):
    threading.Thread(target = start).start()
    #start()


def get_rates(*args, **kwargs):
    portofolio.get_historic_last_days(coin,365)
    


file = open(".\pass.txt", "r")
contents = file.read()
creds = ast.literal_eval(contents)
file.close()

use_default_creds = "n"
while use_default_creds not in ["y", "n"]:
    use_default_creds = input ("Use default credentials (y/n) ?: ")


if use_default_creds == "y":
    # this is the api
    b64secret = "xVTH2f2W9BDG3IQsAq/9qfTZ0HrzQV/rgHZuVvyY6RFQJ1hGspfuTdjnKWXp6lTIDwThm02Y0hlazpDub2F3kw=="
    passphrase="0pliwep0l6t"
    key="8b7bda4c23d10e7539576fd91cc014a3"
else:
    # this is the default
    key = creds["key"]
    b64secret = creds["b64secret"]
    passphrase = creds["passphrase"]
    auth_client = cbpro.AuthenticatedClient(key, b64secret, passphrase)


# initiate database
mongo_client = MongoClient('mongodb://localhost:27017/')

db = mongo_client.cryptocurrency_database

db_orders = db["orders"]

coin = ""
while coin not in ["MIR-EUR","SHIB-EUR", "XTZ-EUR", "AVAX-EUR","1INCH-EUR","MATIC-EUR","CRV-EUR","ICP-EUR","FORTH-EUR","SKL-EUR","ANKR-EUR","LTC-EUR","BCH-EUR", "BNT-EUR", "UMA-EUR","NMR-EUR", "XLM-EUR", "OMG-EUR", "LINK-EUR", "BAND-EUR", "NU-EUR", "FIL-EUR", "ALGO-EUR", "GRT-EUR", "ETC-EUR", "BTC-EUR", "SNX-EUR"]:   
    coin = input("Give input coin: ") or "MATIC-EUR"

db_ticks = db[coin]

enable_movement = "n"
enable_movement = input ("enable movement (use it at your own risk) (y/n) ?: ")



wsClient = myWebsocketClient(api_key = key, api_secret = b64secret, api_passphrase= passphrase, auth=True, channels=None, mongo_collection = db_ticks, should_print = False)


# all the elements will need the figure
figure = plt.figure(figsize=(8,6))

portofolio = Portofolio(figure)
corridor  = Corridor(figure)
penalty = Penalty()
board = Board(figure)




#products = auth_client.get_products()

#print(products)
#print(auth_client.get_product_order_book(product_id="NMR-EUR", level=3))


#auth_client.get_product_24hr_stats("UMA-EUR")



portofolio.get_historic_rates(coin)
portofolio.draw_historic_rates(coin)
portofolio.get_balances()

print ("balance on this coin is: ", portofolio.get_coin_balance(coin))
portofolio.fetch_orders()

axstart = plt.axes([0, 0, 0.1, 0.075])
axhello = plt.axes([0.1, 0, 0.1, 0.075])
axstop = plt.axes([0.2, 0, 0.1, 0.075])
axhistoric_rates = plt.axes([0.5, 0, 0.1, 0.075])


bstart = Button(axstart, 'Start')
bhello = Button(axhello, 'Lanes')
bstop = Button(axstop, 'Stop')
bhistoric = Button(axhistoric_rates, 'Historic')

# widgets.Select(
#     options=['1', '2', '3'],
#     value='2',
#     description='Number:',
#     disabled=False,
# )

bhello.on_clicked(handler)
bstart.on_clicked(start_thread)
bstop.on_clicked(stop_execution)
bhistoric.on_clicked(get_rates)


plt.show()
