from fastapi import FastAPI, HTTPException, Cookie,WebSocket
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import uuid
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
from fastapi.responses import HTMLResponse,RedirectResponse
import starlette.status as status
from fastapi.responses import JSONResponse
import uuid,math,json
import mysql.connector
import dist_tools

DATABASE_URL = "mysql+mysqlconnector://aye:aye@192.168.1.152/wevuuge"

users = dict()
rider_ws = dict()
user_ws = dict()
cooky_dic = dict()
#engine = create_engine(DATABASE_URL)

#config = {
#    "host": "sql.freedb.tech",
#    "user": "freedb_aye256",
#    "password": "#kfTH#mv7u?*TvZ",
#    "database": "freedb_wevuuge"
#}
#"host": "192.168.43.122",
config = {
    "host": "192.168.1.152",
    "user": "root",
    "password": "",
    "database": "wevuuge"
}


#SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

#Base = declarative_base()

app = FastAPI()
conn = mysql.connector.connect(**config)
#static_obj = app.mount("/",StaticFiles(directory="templates"),"static")

page = Jinja2Templates(directory="templates")
#UPDATE `riders` SET `Rider_Status`='0' WHERE 'Rider_Name' = 'maxy';
#UPDATE `users` SET User_Lon='0',User_Lat='0' WHERE Names = 'Avan';
#using limit of 100 km
def findRider(uuid=str(),user_coords=dict()):
    lat = float(user_coords["latitude"])
    lon = float(user_coords["longitude"])
    print(f"\n\ncoordinates {lat} and {lon}")
    east_limit_lat, east_limit_lon = dist_tools.move_point_east(lat,lon,0.1)
    print(f"\\n\neast limit {east_limit_lat} and {east_limit_lon}")
    west_limit_lat, west_limit_lon = dist_tools.move_point_west(lat,lon,0.1)

    north_limit_lat, north_limit_lon = dist_tools.move_point_north(lat,lon,0.1)

    south_limit_lat, south_limit_lon = dist_tools.move_point_south(lat,lon,0.1)
    
    sql_txt = f"SELECT * FROM `riders` WHERE ((Rider_Lon<='{east_limit_lon}' OR Rider_Lon<='{west_limit_lon}' OR Rider_Lon<='{north_limit_lon}' OR Rider_Lon<='{south_limit_lon}') AND (Rider_Lat <='{east_limit_lat}' OR Rider_Lat <='{west_limit_lat}' OR Rider_Lat <='{north_limit_lat}' OR Rider_Lat <='{south_limit_lat}')) AND Rider_Status='1'"

    sql_man = conn.cursor()
    sql_man.execute(sql_txt)
    datax = sql_man.fetchall()
    rider_list = list()
    rider_lon_lats = list()
    rider_id_lists = list()
    near_riders = None
    print(datax)
    if len(datax)>0:
        for datumx in datax:
            if datumx[1] in rider_ws:
                rider_id_lists.append(datumx[1])
                rider_lon_lats.append((float(datumx[6]),float(datumx[5])))
                print(f"riders stuple {rider_lon_lats}")
                near_riders = dist_tools.find_nearest_coordinates_kdtree((lat,lon),rider_lon_lats,rider_id_lists,1)

        return  near_riders
    else:
        return None
def getUserData(cuuid=str()):
    print("getting user")
    sql_txt = f"SELECT Names,User_Contact FROM users WHERE UUID='{cuuid}'"
    usr_cursor = conn.cursor()
    usr_cursor.execute(sql_txt)

    data = usr_cursor.fetchall()
    usr_data = None
    if len(data)>0:
        usr_data = data[0]
    usr_cursor.close()
    return usr_data

def getRiderData(cuuid=str()):
    print("getting user")
    sql_txt = f"SELECT Rider_Name,Rider_Contact FROM riders WHERE UUID='{cuuid}'"
    usr_cursor = conn.cursor()
    usr_cursor.execute(sql_txt)

    data = usr_cursor.fetchall()
    usr_data = None
    print(f"rider  obtained {data}")
    if len(data)>0:
        usr_data = data[0]
    usr_cursor.close()
    print(f"rider  obtained {usr_data}")
    return usr_data



def matchRider(cuuid=str()):
    order_sql = conn.cursor()
    user_sql_txt = f"SELECT Rider_Name,Rider_Contact,Rider_Lon,Rider_Lat,order_id FROM riders WHERE UUID = '{cuuid}'"
    order_sql.execute(user_sql_txt)
    usr_details = order_sql.fetchall()[0]

    usr_data = dict()
    usr_data["names"] = usr_details[0]
    usr_data["telno"] = usr_details[1]
    usr_data["lon"] = usr_details[2]
    usr_data["lat"] = usr_details[3]
    usr_data["order_id"] = usr_details[4]
    

    sql_txt = f"SELECT customer_id FROM orders WHERE rider_id='{cuuid}' AND order_status='order_pending'"

    order_sql = conn.cursor()
    order_sql.execute(sql_txt)
    datum = order_sql.fetchall()[0]
    got_rider_id = datum[0]
    print(f"obtained user: {got_rider_id}")
    usr_data["user_id"] = got_rider_id

    return usr_data


def matchUser(cuuid=str()):
    order_sql = conn.cursor()
    user_sql_txt = f"SELECT NAMES,User_Contact,User_Lon,User_Lat,order_id FROM users WHERE UUID = '{cuuid}'"
    order_sql.execute(user_sql_txt)
    usr_details = order_sql.fetchall()[0]

    usr_data = dict()
    usr_data["names"] = usr_details[0]
    usr_data["telno"] = usr_details[1]
    usr_data["lon"] = usr_details[2]
    usr_data["lat"] = usr_details[3]
    usr_data["order_id"] = usr_details[4]
    

    sql_txt = f"SELECT rider_id FROM orders WHERE customer_id='{cuuid}' AND order_status='order_pending'"

    order_sql = conn.cursor()
    order_sql.execute(sql_txt)
    datum = order_sql.fetchall()[0]
    got_rider_id = datum[0]
    usr_data["rider_id"] = got_rider_id

    return usr_data

def addOrder(cuuid=str(),ruuid=str(),order_dic=None):
    print(order_dic)
    c_id = cuuid
    r_id = ruuid
    price = 5000
    start_lat = order_dic["latitude"]
    start_lon = order_dic["longitude"]
    end_lat = order_dic["to_latitude"]
    end_lon = order_dic["to_latitude"]
    order_stat = "order_pending"
    distance = 5
    order_man= conn.cursor()

    sql_update = f"UPDATE orders SET customer_id='{c_id}',rider_id='{r_id}',price='{price}',start_lat='{start_lat}',start_lon='{start_lon}',end_lat='{end_lat}',end_lon='{end_lon}',order_status='{order_stat}',distance='{distance}' WHERE customer_id='{c_id}' AND rider_id='{r_id}'"

    

    sql_txtx = f"INSERT INTO `orders`(`customer_id`,`rider_id`,`price`,`start_lat`,`start_lon`,`end_lat`,`end_lon`, `order_status`,`distance`) VALUES ('{c_id}','{r_id}','{price}','{start_lat}','{start_lon}','{end_lat}','{end_lon}','{order_stat}','{distance}')"
    
    sql_txt   =f"INSERT INTO orders(customer_id,rider_id,price,start_lat,start_lon,end_lat,end_lon,order_status,distance) VALUES ('{c_id}','{r_id}','{price}','{start_lat}','{start_lon}','{end_lat}','{end_lon}','{order_stat}','{distance}')"

    sql_order_id = f"SELECT order_id FROM orders WHERE (customer_id='{c_id}' AND rider_id='{r_id}') AND order_status='{order_stat}'"

    sql_kill_txt =f"UPDATE riders SET order_id=NULL WHERE UUID='{r_id}'"

    order_man.execute(sql_kill_txt)
    conn.commit()


   


    
    order_man.execute(sql_order_id)
    #conn.commit()

    xgot_order_ids = (order_man.fetchall())
    
    
    print(xgot_order_ids)
    got_order_id = None
    if len(xgot_order_ids) >0:
        o_id = xgot_order_ids[0]
        print(f"deleting order: {o_id}")
        sql_del = f"DELETE FROM orders WHERE `orders`.`order_id` = '{o_id}'"
        order_man.execute(sql_del)
        conn.commit()

        #order_man.execute(sql_order_id)
         #conn.commit()

        #got_order_ids = (order_man.fetchall())[0]

        #got_order_id = got_order_ids[0]

        #sql_up_txt = f"UPDATE riders SET order_id='{got_order_id}' WHERE UUID='{r_id}'"
        #order_man= conn.cursor()
        #order_man.execute(sql_up_txt)
        #conn.commit()
    #else:
    
    order_man.execute(sql_txt)
    conn.commit()

    order_man.execute(sql_order_id)
         #conn.commit()

    got_order_ids = (order_man.fetchall())[0]

    got_order_id = got_order_ids[0]

    sql_up_txt = f"UPDATE riders SET order_id='{got_order_id}' WHERE UUID='{r_id}'"
    order_man= conn.cursor()
    order_man.execute(sql_up_txt)
    conn.commit()
    


    order_man.close()


@app.post("/riderStat")
async def riderStat(request: Request):
    rider_json = await request.json()
    cook_guy = await request.cookies.get("guy_cook")
    cook_type = request.cookies.get("guy_type")

@app.websocket("/approve")
async def approveOrder(websocket: WebSocket):
    print("receieveed web socket")
    await websocket.accept()
    while True:
        datax = await websocket.receive_text()
        print(f"data is {datax}")
        data = json.loads(datax)
        print(f"json  is {data}")
        if "guy_cmd" in data.keys():
            cmd = data["guy_cmd"]
            guy_cook = "fxpro"+data["guy_cook"]
            if guy_cook!=None:
                if data["guy_type"] == "rider":
                    if cmd == "start_scan":
                        print("scan started")
                        rider_ws[guy_cook] = websocket
                    elif cmd == "approve_order":
                        usr_id = matchRider(guy_cook)
                        print(f"approving user : {usr_id}")
                        
                        if usr_id['user_id'] in user_ws.keys():
                            rider_data = getRiderData(guy_cook)
                            rider_ws_json = {}
                            rider_ws_json["name"] = rider_data[0]
                            rider_ws_json["tel"] = rider_data[1]

                            print(f"sending rider data {rider_ws_json}")

                            await user_ws[usr_id['user_id']].send_text(json.dumps(rider_ws_json))
                            print("order approved")
                        else:
                            print("\nerror, no user")
                    else:
                        print("no more commands")
                    print("ono rider")
                elif data["guy_type"] == "customer":
                    print("ono customer")
                    if cmd == "match_user":
                        print(" user scan started")
                        user_ws[guy_cook] = websocket
                        #rider_data_got = matchUser(guy_cook)
                        #xrider_id = rider_data_got["rider_id"]
                        
                        #if  xrider_id in rider_ws.keys():        
                        #    rider_ws[xrider_id].send(json.dumps(rider_data_got))

                    else:
                        print("no more commands")
        else:
            print("error invalid data")

        print(f"websocket data: {data}")
        #await websocket.send_text(f"Message text was: {data}")

async def logCoords(uuid=str(),user_type=str(),user_coords=dict()):
    response = None
    log_cursor = conn.cursor()
    lat = user_coords["latitude"]
    lon = user_coords["longitude"]
    if user_type == 'customer':
            sql_txt = f"UPDATE `users` SET User_Lon='{lon}',User_Lat='{lat}' WHERE UUID = '{uuid}'"

            log_cursor.execute(sql_txt)
            conn.commit()
            content = {"message": "user coords updated"}
            near_pipo = findRider(uuid,user_coords)
            if near_pipo!=None:
                if len(near_pipo) >0:
                    print(f"near pipo: {near_pipo}")
                    response = JSONResponse(content=near_pipo)
                    nearest_rider = near_pipo[0]
                    guy_cook = nearest_rider['id']
                    
                    print(f"this is a customer {lon}, {lat}")
                    print(f"matched to rider: {guy_cook}")
                    #rider_data_got = matchRider(guy_cook)
                    xrider_id = guy_cook
                    #rider_data_got["rider_id"]
                    print(f"sending to rider: {nearest_rider}")
                    if  xrider_id in rider_ws.keys():
                            usr_data = getUserData(uuid)
                            usr_dic = {}
                            usr_dic["names"] = usr_data[0]
                            usr_dic["tel"] = usr_data[1]
                            usr_dic["coords"] = user_coords

                            ws_dic = {}
                            ws_dic["status"] = 200
                            ws_dic["message"] = usr_dic

                            print(f"using user: {ws_dic}")
                            json_str = json.dumps(ws_dic)
                            print(f"using user string: {json_str}")
                            await rider_ws[xrider_id].send_text(json_str)
                            addOrder(uuid,nearest_rider['id'],user_coords)
                            content = {"status":200,"message": nearest_rider}
                            response = JSONResponse(content=content)
                            
                else:
                    content = {"status":400,"message": "no riders"}
                    response = JSONResponse(content=content)
            else:
                content = {"status":400,"message": "no rider nearby"}
                print("no rider waiting")
                response = JSONResponse(content=content)
            

            response = JSONResponse(content=content)

    elif user_type == 'rider':
            sql_txt = f"UPDATE `riders` SET Rider_Status='1',Rider_Lon='{lon}',Rider_Lat='{lat}' WHERE UUID = '{uuid}'"
            log_cursor.execute(sql_txt)
            conn.commit()
            content = {"status":200,"message": "rider akimbo"}
            response = JSONResponse(content=content)
            print(f"this is a rider {lon}, {lat}")
    else:
            print("user_error")
            content = {"status":404,"message": "user error"}
            response = JSONResponse(content=content)
    log_cursor.close()
    return response

conn = mysql.connector.connect(**config)

class Customer:
    
    ctable_name = "users"
   
    def __init__(self,name=str(),telephone=str(),passcode=None,user_type=None,uuid=str()):
        self.msg = str()
        self.bmsg = False
        print(f"adding user {uuid}")
        a_cursor = conn.cursor()
        sql_txt = f"SELECT * FROM `users` WHERE User_Contact ='{telephone}' AND passcode = '{passcode}'"

        print(f"execting data {sql_txt}")
        a_cursor.execute(sql_txt)
        data = a_cursor.fetchall()
        print(data)

        if len(data) <= 0:
            sql_in_txt = f"INSERT INTO `users`(`Names`,`UUID`, `User_Contact`, `passcode`) VALUES ('{name}','{uuid}','{telephone}','{passcode}')"
            a_cursor.execute(sql_in_txt)
            conn.commit()
            self.msg = "user_added"
            self.bmsg = True
            print("no user")
        else:
            self.msg = "user_active_already"
            print("user already present")
        a_cursor.close()
    def getStatus(self):
        print(f"msg is: {self.msg}")
        return self.msg

class Rider:
    #conn = mysql.connector.connect(**config)
    #ctable_name = "riders"
    
    def __init__(self,name=str(),telephone=str(),passcode=None,user_type=None,uuid=str()):
        self.msg = str()
        self.bmsg = False
        print(f"adding user {uuid}")
        a_cursor = conn.cursor()
        sql_txt = f"SELECT * FROM `riders` WHERE Rider_Contact ='{telephone}' AND passcode = '{passcode}'"

        print(f"exectinf data {sql_txt}")
        a_cursor.execute(sql_txt)
        data = a_cursor.fetchall()
        print(data)
        #UPDATE `riders` SET `Rider_Status`='0' WHERE 'Rider_Name' = 'maxy';
        if len(data) <= 0:
            rsttatus = False
            sql_in_txt = f"INSERT INTO `riders`(`UUID`,`Rider_Name`, `Rider_Contact`, `passcode`) VALUES ('{uuid}','{name}','{telephone}','{passcode}')"
            a_cursor.execute(sql_in_txt)
            conn.commit()
            self.bmsg = True
            self.msg = "user_added"
            print("no user")
        else:
            self.msg = "user_active_already"
            print("user already present")
        a_cursor.close()
    def getStatus(self):
        print(f"msg is: {self.msg}")
        return self.msg

async def parseReq(request: Request):
    try:
        content = await request.body()
        # Assuming the content is in a form that can be converted to a dictionary, for example, URL-encoded data like "key1=value1&key2=value2"
        data_str = content.decode('utf-8')  # Decode the bytes to a string
        data_list = data_str.split('&')  # Split by "&" to get key-value pairs
        data_dict = {}
        for item in data_list:
            key, value = item.split('=')
            data_dict[key] = value
        return data_dict
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": "Invalid data format"})


def serveUser(request: Request):
    cooky = request.cookies.get("guy_cook")

@app.get("/", response_class=JSONResponse)
async def servePage(request: Request):
    cooky = request.cookies.get("guy_type")
    if cooky == None:
        message = {"status":201}
        return JSONResponse(content=message)
        #return page.TemplateResponse("index.html",{"request": request})
    else:
        cooky_val = "fxpro"+(request.cookies.get("guy_cook"))
        print(f"cookie yeah {cooky_val}")
        if cooky == "customer":
            user_data = getUserData(cooky_val)
            message = {"status":200,"body":{"user_names":user_data[0],"user_type":"customer"}}
            return JSONResponse(content=message)
            #return page.TemplateResponse("user.html",{"request": request,'fast_user_names':user_data[0],'fast_user_type':'customer'})
        elif cooky == "rider":

            rider_data = getRiderData(cooky_val)
            message = {"status":200,"body":{"user_names":rider_data[0],"user_type":"rider"}}
            return JSONResponse(content=message)
            #return page.TemplateResponse("rider.html",{"request": request,'fast_user_names':rider_data[0],'fast_user_type':'rider'})
        else:
            message = {"status":400}
            return JSONResponse(content=message)
            #return None

@app.get("/red", response_class=HTMLResponse)
async def reservePage(request: Request):
    cooky = request.cookies.get("guy_cook")
    if cooky == None:
        return page.TemplateResponse("user.html",{"request": request})
    else:
        await register_user(request)

@app.post("/registerx")
async def regUser(request: Request):
    req_data = await request.json()
    print(req_data)#["name"])
    redirect_url = "/red"
    print(f"url is: {redirect_url}\n\n")
    content = {"status":200,"redirect":redirect_url}
    response_json = JSONResponse(content)
    return response_json
    #RedirectResponse(redirect_url,status_code=status.HTTP_302_FOUND)

@app.post("/orderRide")
async def completeOrder(request:Request):
    req_data = await request.json()
    print(req_data)


def authUser(user_tel=str(),user_pwd=str()):

    usql_txt = f"SELECT UUID FROM users WHERE User_Contact = '{user_tel}'"
    rsql_txt = f"SELECT UUID FROM riders WHERE Rider_Contact = '{user_tel}'"

    user_chcks = conn.cursor()
    user_chcks.execute(usql_txt)

    uuids = user_chcks.fetchall()
    print(f"uuids: {uuids}")
    res_uuid = list()
    if len(uuids) > 0:
        usr_uuid = uuids[0][0]
        print(f"gotten user uuid {usr_uuid}")
        #res_uuid = {}
        #res_uuid = usr_uuid

        res_uuid.append("customer")
        res_uuid.append(usr_uuid)
    else:
        user_chcks.execute(rsql_txt)
        ruuids = user_chcks.fetchall()

        if len(ruuids) > 0:
            ruuid = ruuids[0][0]
            print(f"gotten rider uuid {ruuid}")
            res_uuid.append("rider")
            res_uuid.append(ruuid)
            #res_uuid = ruuid
    print(f"sending uuids {res_uuid}")
    return res_uuid


@app.post("/login")
async def login_user(request: Request):
    
    json_request = await request.json()
    print(json_request)
    user_tel = json_request["telephone"]
    user_pwd = json_request["passcode"]

    cook = authUser(user_tel,user_pwd)
    response = None
    if len(cook) > 0:
        redirect_url = "/"
        jcontent = {"status":200,"redirect":redirect_url}
        response = JSONResponse(content = jcontent)
        response.set_cookie(key="guy_type",value=cook[0].replace("fxpro",''))
        response.set_cookie(key="guy_cook",value=cook[1].replace("fxpro",''))
    else:
         jcontent = {"status":404,"message":"user error"}
         response = JSONResponse(content = jcontent)
    return response





@app.post("/register")
async def register_user(request: Request):
    cooky = request.cookies.get("guy_cook")
    print(f"cookie: {cooky}")
    redirect_url = "/"
    customer = None
    response = None
    if cooky == None:
        print("NO COOKIE")
        
    else:
        print("COOKIE HERE")
        #content = {"message": "cookie login succes"}
        #response = JSONResponse(content=content)
        #return response
        #customer = cooky_dic[cooky]
    #return response
    customer = await request.json()
    name = customer['name']
        
    telno = customer['telephone']
    cpass = customer['passcode']
    user_type = customer['user_type']

    if user_type == "customer":
        new_uuid = str(uuid.uuid4())
        print(f"uuid is: {new_uuid}")
        customer["uuid"] = "fxpro"+new_uuid
        cuuid = customer["uuid"]
        print(f"uuid is: {cuuid}")
        print(f"customer is {customer}")
        user_o = Customer(**customer)
        if user_o.getStatus() == "user_added":
            content = {"status":200,"redirect":redirect_url}
            response = JSONResponse(content=content)
            response.set_cookie(key="guy_cook", value=new_uuid)
            response.set_cookie(key="guy_type",value = user_type)
        #cooky_dic[cuuid] = customer
            print(f"user at: {customer['name']}")
        elif user_o.getStatus() == "user_active_already":
            content = {"status":200,"redirect":redirect_url}
            #response = JSONResponse(content=content)
        else:
            content = {"message": "login error"}
            response = JSONResponse(content=content)
    elif user_type == "rider":
        rnew_uuid = str(uuid.uuid4())
        print(f"uuid is: {rnew_uuid}")
        customer["uuid"] = "fxpro"+rnew_uuid
        rcuuid = customer["uuid"]
        print(f"uuid is: {rcuuid}")
        print(f"rider is {customer}")
        rider_o = Rider(**customer)
        rstat = rider_o.getStatus() 
        if rstat == "user_added":
            print('user added')
            rcontent = {"message": "login succes"}
            content = {"status":200,"redirect":redirect_url}
            response = JSONResponse(content=content)
            
            response.set_cookie(key="guy_cook", value=rnew_uuid)
            response.set_cookie(key="guy_type",value = user_type)
        elif rider_o.getStatus() == "user_active_already":
            content = {"message": "cookie ll login succes"}
            content = {"status":200,"redirect":redirect_url}
            response = JSONResponse(content=content)
        else:
            content = {"message": "login error"}
            response = JSONResponse(content=content)
        #cooky_dic[rcuuid] = customer
        print(f"rider at: {customer['name']}")
        
    else:
        content = {"message": "invalid user"}
        response = JSONResponse(content=content)
    redirect_url = "/red"
    print(f"url is: {redirect_url}\n\n")
    
    #response_json = JSONResponse(content)
    return response
    #return response

@app.post("/lookrider")
async def riderEye(request: Request):
    print(cooky_dic)
    cooky = request.cookies.get("guy_cook")
    cook_type = request.cookies.get("guy_type")
    print(f"cookie: {cooky}")
    print(f"cookie_type: {cook_type}")
    customer = None
    response = None
    if cooky == None:
        print("NO COOKIE")
        content = {"status":401,"message": "please login 1st"}
        response = JSONResponse(content=content)
        return response
    else:
        print("COOKIE HERE")
        active_point = "fxpro"+cooky
        #cooky_dic["fxpro"+cooky]
        active_coords = await request.json()
        alat = active_coords["latitude"]
        alon = active_coords["longitude"]
        print(f"coords are: {alat} and {alon}")
        auser_type = cook_type

        if auser_type == 'customer':
            print("this is a customer")
            response = await logCoords(active_point,auser_type,active_coords)
        elif auser_type == 'rider':
            response = await logCoords(active_point,auser_type,active_coords)
            print("this is a rider")
        else:
            print("user_error")
            content = {"message": "user error"}
            response = JSONResponse(content=content)
        return response
    print("lookup driver")


@app.post("/drivers/")
def register_driver(name: str, latitude: float, longitude: float):
    driver_id = str(uuid.uuid4())
    driver = Driver(id=driver_id, name=name, latitude=latitude, longitude=longitude)

    db = SessionLocal()
    db.add(driver)
    db.commit()
    db.close()

    return driver

@app.post("/ride-requests/")
def submit_ride_request(user_latitude: float, user_longitude: float, dest_latitude: float, dest_longitude: float):
    request_id = str(uuid.uuid4())
    ride_request = RideRequest(
        id=request_id,
        user_latitude=user_latitude,
        user_longitude=user_longitude,
        dest_latitude=dest_latitude,
        dest_longitude=dest_longitude,
    )

    #db = SessionLocal()
    #db.add(ride_request)
    #db.commit()
    #db.close()

    # Find the nearest available driver and assign the ride request to them
    nearest_driver = find_nearest_driver(ride_request.id, ride_request.user_latitude, ride_request.user_longitude)
    if nearest_driver:
        ride_request.status = "accepted"
        ride_request.assigned_driver_id = nearest_driver.id
    else:
        ride_request.status = "pending"

    #db = SessionLocal()
    #db.add(ride_request)
    #db.commit()
    #db.close()

    return ride_request

#def find_nearest_driver(ride_request_id, user_latitude, user_longitude):
def find_nearest_driver(user_location):
    # Define a maximum distance for considering drivers
    max_distance_km = 10.0

    drivers = []
    for data in driver_data:
        driver = Driver(name=data["name"], latitude=data["latitude"], longitude=data["longitude"])
        drivers.append(driver)

    available_drivers = [driver for driver in drivers if not any(request.assigned_driver.id == driver.id for request in ride_requests)]
    
    if not available_drivers:
        return None

    nearest_driver = min(available_drivers, key=lambda driver: geodesic(driver.location, user_location).kilometers)

    if geodesic(nearest_driver.location, user_location).kilometers > max_distance_km:
        return None

    return nearest_driver

@app.put("/ride-requests/{ride_request_id}/response/")
def driver_response(ride_request_id: str, status: str):
    db = SessionLocal()
    ride_request = db.query(RideRequest).filter(RideRequest.id == ride_request_id).first()

    if not ride_request:
        db.close()
        raise HTTPException(status_code=404, detail="Ride request not found.")

    if ride_request.status == "pending":
        db.close()
        raise HTTPException(status_code=400, detail="Ride request has not been accepted yet.")

    if status.lower() == "accept":
        ride_request.status = "accepted"
    elif status.lower() == "decline":
        ride_request.status = "declined"
    else:
        db.close()
        raise HTTPException(status_code=400, detail="Invalid response status.")

    db.commit()
    db.close()

    return ride_request
