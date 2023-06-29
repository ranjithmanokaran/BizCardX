import streamlit as st
import easyocr
import mysql.connector
from mysql.connector import Error
from PIL import Image
import base64
import io
import os
import cv2
import matplotlib.pyplot as plt
import pandas as pd
import re

reader = easyocr.Reader(['en'])

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host='127.0.0.1',
            database='bizcardx',
            user='root',
            password='$Gb35'
        )
        if conn.is_connected():
            return conn
    except Error as e:
        st.error(f"Error connecting to MySQL database: {e}")

# Initialize session state
if 'user' not in st.session_state:
    st.session_state.user = None
    
class User:
    def __init__(self, username):
        self.username = username

def authenticate(username, password):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "SELECT * FROM users WHERE username = %s"
        cursor.execute(query, (username,))
        user = cursor.fetchone()
        
        if user is not None and user[2] == password:
            return User(user[0])
        
        cursor.close()
        conn.close()
    except Error as e:
        st.error(f"Error retrieving user: {e}")
    return None

def signup(username, password):
    try:
        conn = get_db_connection()
        create_usert_if_not_exists(conn)
        cursor = conn.cursor()
        query = "INSERT INTO users (username, password) VALUES (%s, %s)"
        cursor.execute(query, (username, password))
        conn.commit()
        
        cursor.close()
        conn.close()
        return True
    except Error as e:
        st.error(f"Error creating user: {e}")
    
    return False

def login():
    if 'user' not in st.session_state:
        st.session_state.user = None

    if st.session_state.user is not None:
        st.experimental_rerun()

    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    login_button = st.button("Log In")
    signup_button = st.button("Sign Up")

    if login_button:
        user = authenticate(username, password)
        if user is not None:
            st.session_state.user = username
            st.success("Logged in successfully!")
            st.experimental_rerun()
        else:
            st.error("Invalid username or password")

    if signup_button:
        signup_form()


def signup_form():
    # Display the signup form to the user
    # Handle the user signup process
    st.title("Sign Up")
    username = st.text_input("Username", key="signup_username")
    password = st.text_input("Password", type="password", key="signup_password")
    confirm_password = st.text_input("Confirm Password", type="password", key="signup_confirm_password")
    signup_button = st.button("Sign Up", key="signup_button")

    if signup_button:
        if password == confirm_password:
            success = signup(username, password)
            if success:
                st.success("User created successfully!")
            else:
                st.error("Error creating user. Please try again.")
        else:
            st.error("Passwords do not match.")

            
def create_table_if_not_exists(conn):
    try:
        cursor = conn.cursor()
        create_table_query = '''
           CREATE TABLE IF NOT EXISTS card_data
                     (Id INTEGER PRIMARY KEY AUTO_INCREMENT,
                      User TEXT,
                      CompanyName TEXT,
                      CardHolder TEXT,
                      Designation TEXT,
                      Phone VARCHAR(50),
                      Email TEXT,
                      Website TEXT,
                      Area TEXT,
                      City TEXT,
                      State TEXT,
                      PinCode VARCHAR(10),
                      Image LONGBLOB
                      )
        '''
        cursor.execute(create_table_query)
        conn.commit()
    except Error as e:
        st.error(f"Error creating table: {e}")
        
def create_usert_if_not_exists(conn):
    try:
        cursor = conn.cursor()
        create_table_query = '''
            CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(255) UNIQUE NOT NULL,
        password VARCHAR(255) NOT NULL
    )
        '''
        cursor.execute(create_table_query)
        conn.commit()
    except Error as e:
        st.error(f"Error creating table: {e}")
        

    

def save_to_database(data, image):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    insert_query = '''
        INSERT INTO business_cards (name, email, phone, image_data)
        VALUES (%s, %s, %s, %s)
    '''
    image_data = image.tobytes()
    card_data = (data['name'], data['email'], data['phone'], image_data)
    cursor.execute(insert_query, card_data)
    conn.commit()
    
    cursor.close()
    conn.close()

    
def process_image(uploaded_card):
    def save_card(uploaded_card):
        with open(os.path.join("uploaded_cards",uploaded_card.name), "wb") as f:
            f.write(uploaded_card.getbuffer())   
    save_card(uploaded_card)
    
    def image_preview(image,res): 
        for (bbox, text, prob) in res: 
          # unpack the bounding box
            (tl, tr, br, bl) = bbox
            tl = (int(tl[0]), int(tl[1]))
            tr = (int(tr[0]), int(tr[1]))
            br = (int(br[0]), int(br[1]))
            bl = (int(bl[0]), int(bl[1]))
            cv2.rectangle(image, tl, br, (0, 255, 0), 2)
            cv2.putText(image, text, (tl[0], tl[1] - 10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
        plt.rcParams['figure.figsize'] = (15,15)
        plt.axis('off')
        plt.imshow(image)
    
    # DISPLAYING THE UPLOADED CARD
    col1,col2 = st.columns(2,gap="large")
    with col1:
        st.markdown("#     ")
        st.markdown("#     ")
        st.markdown("### You have uploaded the card")
        st.image(uploaded_card)
    # DISPLAYING THE CARD WITH HIGHLIGHTS
    with col2:
        st.markdown("#     ")
        st.markdown("#     ")
        with st.spinner("Please wait processing image..."):
            st.set_option('deprecation.showPyplotGlobalUse', False)
            saved_img = os.getcwd()+ "\\" + "uploaded_cards"+ "\\"+ uploaded_card.name
            image = cv2.imread(saved_img)
            res = reader.readtext(saved_img)
            st.markdown("### Image Processed and Data Extracted")
            st.pyplot(image_preview(image,res))  
            
        
    #easy OCR
    saved_img = os.getcwd()+ "\\" + "uploaded_cards"+ "\\"+ uploaded_card.name
    result = reader.readtext(saved_img,detail = 0,paragraph=False)
    
    # CONVERTING IMAGE TO BINARY TO UPLOAD TO SQL DATABASE
    def img_to_binary(file):
        # Convert image data to binary format
        with open(file, 'rb') as file:
            binaryData = file.read()
        return binaryData
    
    data = {"user": st.session_state.user,
            "CompanyName" : [],
            "CardHolder" : [],
            "Designation" : [],
            "Phone" :[],
            "Email" : [],
            "Website" : [],
            "Area" : [],
            "City" : [],
            "State" : [],
            "PinCode" : [],
            "Image" : img_to_binary(saved_img)
           }

    def get_data(res):
        for ind,i in enumerate(res):
            # To get WEBSITE_URL
            if "www " in i.lower() or "www." in i.lower():
                data["Website"].append(i)
            elif "WWW" in i:
                data["Website"] = res[4] +"." + res[5]

            # To get EMAIL ID
            elif "@" in i:
                data["Email"].append(i)

            # To get MOBILE NUMBER
            elif "-" in i:
                data["Phone"].append(i)
                if len(data["Phone"]) ==2:
                    data["Phone"] = " & ".join(data["Phone"])

            # To get COMPANY NAME  
            elif ind == len(res)-1:
                data["CompanyName"].append(i)

            # To get CARD HOLDER NAME
            elif ind == 0:
                data["CardHolder"].append(i)

            # To get DESIGNATION
            elif ind == 1:
                data["Designation"].append(i)

            # To get AREA
            if re.findall('^[0-9].+, [a-zA-Z]+',i):
                data["Area"].append(i.split(',')[0])
            elif re.findall('[0-9] [a-zA-Z]+',i):
                data["Area"].append(i)

            # To get CITY NAME
            match1 = re.findall('.+St , ([a-zA-Z]+).+', i)
            match2 = re.findall('.+St,, ([a-zA-Z]+).+', i)
            match3 = re.findall('^[E].*',i)
            if match1:
                data["City"].append(match1[0])
            elif match2:
                data["City"].append(match2[0])
            elif match3:
                data["City"].append(match3[0])
            else:
                if len(data["City"])==0 or data["City"][0] != None:
                    data["City"].append(None)

            # To get STATE
            state_match = re.findall('[a-zA-Z]{9} +[0-9]',i)
            if state_match:
                 data["State"].append(i[:9])
            elif re.findall('^[0-9].+, ([a-zA-Z]+);',i):
                data["State"].append(i.split()[-1])
            if len(data["State"])== 2:
                data["State"].pop(0)
            else:
                if  len(data["State"])==0 or data["State"][0] != None:
                    data["State"].append(None)

            # To get PINCODE        
            if len(i)>=6 and i.isdigit():
                data["PinCode"].append(i)
            elif re.findall('[a-zA-Z]{9} +[0-9]',i):
                data["PinCode"].append(i[10:])
            else:
                if  len(data["PinCode"])==0 or data["PinCode"][0] != None:
                    data["PinCode"].append(None)
            
    get_data(result)
    

    
    #FUNCTION TO CREATE DATAFRAME
    def create_df(data):
        df = pd.DataFrame(data)
        return df
    df = create_df(data)
    st.success("### Data Extracted!")
    st.write(df)
    conn = get_db_connection()
    cursor = conn.cursor()
    if st.button("Upload to Database"):
        create_table_if_not_exists(conn)
        for i,row in df.iterrows():
            #here %S means string values 
            sql = """INSERT INTO card_data(User,CompanyName,CardHolder,Designation,Phone,Email,Website,Area,City,State,PinCode,Image)
                     VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
            cursor.execute(sql, tuple(row))
            # the connection is not auto committed by default, so we must commit to save our changes
            conn.commit()
        st.success("#### Uploaded to database successfully!")

            


def main():
    if st.session_state.user is None:
        login()
    else:
        st.title("Business Card Extraction")
        st.write("Upload an image of a business card")
        uploaded_card = st.file_uploader("upload here",label_visibility="collapsed",type=["png","jpeg","jpg"])
            
        if uploaded_card is not None:
           process_image(uploaded_card)
            
        logout_button = st.button("Log Out")
        if logout_button:
            st.session_state.user = None
            st.info("Logged out successfully!")
            st.experimental_rerun()




if __name__ == '__main__':
    main()
