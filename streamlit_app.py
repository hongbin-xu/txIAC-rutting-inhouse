import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from scipy import ndimage
import plotly.graph_objects as go
from scipy.interpolate import griddata

st.set_page_config(layout="wide", 
                   page_title='IAC-Rutting Verification',
                   menu_items={
                       'Get help': "mailto:hongbinxu@utexas.edu",
                       'About': "Developed and maintained by Hongbin Xu"})

# Authentication function
def check_password():
    """Returns `True` if the user had a correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if (
            st.session_state["username"] in st.secrets["passwords"]
            and st.session_state["password"]
            == st.secrets["passwords"][st.session_state["username"]]
        ):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store username + password
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show inputs for username + password.
        st.text_input("Username", on_change=password_entered, key="username")
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.text_input("Username", on_change=password_entered, key="username")
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 User not known or password incorrect")
        return False
    else:
        # Password correct.
        return True

@st.cache_data
def dataLoad(_conn):#, segID=None, idmin = None, idmax=None):
    """
    mode1: select for each segment
    mode2: select for multiple segment
    """
    data = conn.query('SELECT * from 20mph_Grided_data_DistanceCorrected_longformat')# WHERE id BETWEEN '+ str(idmin) +' AND ' + str(idmax)+';')
    return data

#""" @st.cache_data
#def outlierRemove(data, lower, upper):
#    data_filtered = data.copy()
#    outlier_location = data_filtered.loc[(data_filtered["height"]<lower)|(data_filtered["height"]>upper), ["transID", "lonID"]]    
#    outlier_replace = griddata(points = (data_filtered["lonID"].values, data_filtered["transID"].values), values=data_filtered["height"].values.reshape(-1,1),
#                            xi = (outlier_location["lonID"].values, outlier_location["transID"].values), method="linear")
#    data_filtered.loc[(data_filtered["height"]<lower)|(data_filtered["height"]>upper), "height"] = outlier_replace
#    return data_filtered """

@st.cache_data
def outlierRemove(data, lower, upper):
    data_filtered = data.copy()
    data_filtered.loc[data_filtered["height"]<lower, "height"] = lower
    data_filtered.loc[data_filtered["height"]>upper, "height"] = upper
    return data_filtered

@st.cache_data
def dataProc(data, filterType, kneighbors):
    ncol = data["transID"].max()+1
    dataArray = data["height"].copy().values.reshape([-1, ncol])
    data_filtered = data.copy().drop(columns = "height")
    # Filter data
    if filterType == "median":
        dataArray = ndimage.median_filter(dataArray, size=(kneighbors, kneighbors))
    if filterType == "mean":
        dataArray = ndimage.uniform_filter(dataArray, size=(kneighbors, kneighbors))
    data_filtered["height"] = dataArray.flatten()
    return data_filtered

@st.cache_data
def heightHist(data):
    fig = px.histogram(data, x = "height")
    fig.update_layout(hovermode="x unified", height = 300)
    st.plotly_chart(fig, use_container_width=True, theme = None)

@st.cache_data
def heightCdf(data):
    fig = px.ecdf(data, x = "height")
    fig.update_layout(hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True, theme = None)

@st.cache_data
def transExtrac(data, data_filtered, id):
    # Extract transverse profile
    transProfile = data.loc[data["lonID"]==id].reset_index(drop=True).rename(columns = {"height": "original"})
    transProfile["filtered"] = data_filtered.loc[data_filtered["lonID"]==id, "height"].values
    transProfile = pd.melt(transProfile, id_vars = ["id", "lonID", "lonOFFSET", "transID", "transOFFSET"], value_vars = ["original", "filtered"], var_name = "filter", value_name = "height")
    
    # Plot transverse profile
    fig = px.line(transProfile, x="transID", y="height", color = "filter", labels = {"DIST": "Transverse OFFSET (mm)", "Height": "Height (mm}"}, template = "plotly_dark")
    st.plotly_chart(fig, use_container_width=True, theme = None)
    return transProfile

@st.cache_data
def lonExtrac(data, data_filtered, id):
    lonProfile = data.loc[data["transID"]==id].reset_index(drop=True).rename(columns = {"height": "original"})
    lonProfile["filtered"] = data_filtered.loc[data_filtered["transID"]==id, "height"].values
    lonProfile = pd.melt(lonProfile, id_vars = ["id", "lonID", "lonOFFSET", "transID", "transOFFSET"], value_vars = ["original", "filtered"], var_name = "filter", value_name = "height")

    fig = px.line(lonProfile, x ="lonID", y="height", color = "filter", labels = {"id": "Longitudinal id","Height": "Height (mm}"}, template = "plotly_dark")
    st.plotly_chart(fig, use_container_width=True, theme = None)
    return lonProfile

@st.cache_data
def surfOrigin(data):
    # hover information
    z = data["height"].values.reshape([425, -1])
    fig = go.Figure(data=[go.Surface(z=z, x=np.arange(4096), y=np.arange(425))])
    fig.update_layout(title = "Original", scene=dict(xaxis_title="Transverse ID", yaxis_title="Longitudinal ID", zaxis_title="height", zaxis = dict(range=[-0.3,0.25])),template="plotly", height = 600)
    fig.update_traces(hovertemplate = "<b>TransID</b>: %{x}<br>" + "<b>lonID</b>: %{y}<br>"+ "<b>Height</b>: %{z}<br>")
    #fig['layout']['xaxis']['autorange'] = "reversed"
    st.plotly_chart(fig, use_container_width=True, theme = None)

@st.cache_data
def surFiltered(data):
    # hover information
    z = data["height"].values.reshape([425, -1])
    fig = go.Figure(data=[go.Surface(z=z, x=np.arange(4096), y=np.arange(425))])
    fig.update_layout(title = "Filtered", scene=dict(xaxis_title="Transverse ID", yaxis_title="Longitudinal ID", zaxis_title="height", zaxis = dict(range=[-0.3,0.25])),template="plotly", height = 600)
    fig.update_traces(hovertemplate = "<b>TransID</b>: %{x}<br>" + "<b>lonID</b>: %{y}<br>"+ "<b>Height</b>: %{z}<br>")
    #fig['layout']['xaxis']['autorange'] = "reversed"
    st.plotly_chart(fig, use_container_width=True, theme = None)

# Check authentication
if check_password():    
    # Page title
    conn = st.experimental_connection("mysql", type="sql")
    st.session_state.data = dataLoad(_conn=conn)

    with st.sidebar:
        st.header("IAC-Rutting (TxDOT)")
        with st.container():
            st.subheader("Suface")
            col11, col12 = st.columns(2)
            with col11:
                idmin = st.number_input("id start", min_value=0, max_value=423, value = 0, step= 1, disabled = True)
                
            with col12:
                idmax = st.number_input("id end", min_value=idmin, max_value=424, value = 424, step= 1, disabled = True)

            st.subheader("Filter")
            st.write("Outliers")
            col13, col14 = st.columns(2)
            with col13: 
                lower_bound = st.number_input("lower bound", min_value = st.session_state.data["height"].min(), max_value=st.session_state.data["height"].max(), value = 0.03)
            with col14: 
                upper_bound = st.number_input("lower bound", min_value = st.session_state.data["height"].min(), max_value=st.session_state.data["height"].max(), value = 0.15)

            if st.button("Remove outliers"):
                st.session_state.data_filtered = outlierRemove(data=st.session_state.data, lower = lower_bound, upper = upper_bound)
            
            st.write("Smoothing")
            col15, col16 = st.columns(2)
            with col15:
                filterType = st.selectbox("Select filter", options = ["mean", "median"], index = 1)
            with col16:
                kneighbors = st.selectbox("Window size", options = [3, 5, 7, 9, 11, 15, 25], index =0)
            if st.button("Apply"):
                st.session_state.data_filtered = dataProc(data=st.session_state.data_filtered, filterType=filterType, kneighbors=kneighbors)
            
            st.subheader("Inspect profiles")
            id_ = st.number_input("Transverse profile", min_value=idmin, max_value=idmax, step = 1)
            id_x = st.number_input("Longitudinal profile", min_value=0, max_value=4095,value=0, step = 1)


    # MySQL connection
    st.subheader("Suface")
    with st.container():
        heightHist(data=st.session_state.data)
    col1, col2 = st.columns(2)
    with col1:
        with st.container():
            if 'data' in st.session_state:
                # plot surface
                surfOrigin(data=st.session_state.data)
    with col2:
        with st.container():
            if 'data_filtered' in st.session_state:
                surFiltered(data=st.session_state.data_filtered)

    
    col1, col2 = st.columns(2)
    if 'data_filtered' in st.session_state:
        with col1:
            with st.container():
                st.subheader("Transverse Profile")
                trans_profile = transExtrac(data = st.session_state.data, data_filtered = st.session_state.data_filtered, id=id_)
                # View and download data
                st.download_button(label="Download transverse profile", data=trans_profile.to_csv().encode('utf-8'), file_name="transProfile_" +str(id_)+".csv", mime = "csv")
        with col2:
            with st.container():
                st.subheader("Longitudinal Profile")
                # Extract transverse profile
                lon_profile = lonExtrac(data = st.session_state.data, data_filtered = st.session_state.data_filtered, id=id_x)
                
                # View and download data
                st.download_button(label="Download longitudinal profile", data=lon_profile.to_csv().encode('utf-8'), file_name="lonProfile_" +str(id_x)+"_"+ str(idmin) +" to " + str(idmax)+ ".csv", mime = "csv")

    
    
