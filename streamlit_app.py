import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from scipy import ndimage
import plotly.graph_objects as go

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


@st.cache_data
def dataProc(data, filterType, kneighbors):
    ncol = data["transID"].max()+1
    dataArray = data["height"].values.reshape([-1, ncol])
    data_filtered = data.copy().drop(columns = "height")
    # Filter data
    if filterType == "median":
        dataArray = ndimage.median_filter(dataArray, size=(kneighbors, kneighbors))
    
    if filterType == "mean":
        dataArray = ndimage.uniform_filter(dataArray, size=(kneighbors, kneighbors))
    data_filtered["height"] = dataArray.flatten()
    return data_filtered


@st.cache_data
def transExtrac(data, data_filtered, id):
    # Extract transverse profile
    transProfile = data.loc[data["lonID"]==id].reset_index(drop=True).rename(columns = {"height": "original"})
    transProfile["filtered"] = data_filtered.loc[data_filtered["lonID"]==id, "height"].values
    transProfile = pd.melt(transProfile, id_vars = ["id", "lonID", "lonOFFSET", "transID", "transOFFSET"], value_vars = ["height", "filtered"], var_name = "filter", value_name = "height")
    
    # Plot transverse profile
    fig = px.line(scanData_v1, x="DIST", y="Height", labels = {"DIST": "Transverse OFFSET (mm)", "Height": "Height (mm}"}, template = "plotly_dark")
    fig.layout.yaxis.range = [0,max_val]
    st.plotly_chart(fig, use_container_width=True, theme = None)
    return transProfile

@st.cache_data
def lonExtrac(data, data_filtered, id, ):
    lonProfile = data.loc[data["transID"]==id].reset_index(drop=True).rename(columns = {"height": "original"})
    lonProfile["filtered"] = data_filtered.loc[data_filtered["transID"]==id, "height"].values
    lonProfile = pd.melt(lonProfile, id_vars = ["id", "lonID", "lonOFFSET", "transID", "transOFFSET"], value_vars = ["height", "filtered"], var_name = "filter", value_name = "height")

    fig = px.line(scanData, x ="id", y="Height", labels = {"id": "Longitudinal id","Height": "Height (mm}"}, template = "plotly_dark")
    fig.layout.yaxis.range = [0,max_val]
    st.plotly_chart(fig, use_container_width=True, theme = None)
    return lonProfile

@st.cache_data
def surfPlot(data, data_filtered):
    # hover information
    z = data["height"].values.reshape([425, -1])
    fig = go.Figure(data=[go.Surface(z=z, x=np.arange(4096), y=np.arange(425))])
    fig.update_layout(scene=dict(xaxis_title="Transverse ID",
                      yaxis_title="Longitudinal ID", zaxis_title="height"))

    #fig['layout']['xaxis']['autorange'] = "reversed"
    st.plotly_chart(fig, use_container_width=True, theme = None)

# Check authentication
if check_password():    
    # Page title
    conn = st.experimental_connection("mysql", type="sql")
    st.session_state.data = dataLoad(_conn=conn)

    # MySQL connection
    col1, col2 = st.columns(2, gap = "medium")
    with col1:
        with st.container():
            st.subheader("Suface")
            col11, col12 = st.columns(2)
            with col11:
                idmin = st.number_input("id start", min_value=0, max_value=423, value = 0, step= 1)
                idmax = st.number_input("id end", min_value=idmin, max_value=424, value = 424, step= 1)
                # Load data
                if st.button("Update"):
                    st.write(st.session_state.data.head())

            with col12:
                filterType = st.selectbox("Select filter", options = ["mean", "median"], index = 1)
                kneighbors = st.selectbox("Window size", options = [3, 5, 7, 9], index =0)
                if st.button("Apply filter"):
                    st.session_state.data_filtered = dataProc(data=st.session_state.data, filterType=filterType, kneighbors=kneighbors)
                    st.write(st.session_state.data_filtered.head())
            if 'data' in st.session_state:
                # plot surface
                surfPlot(data=st.session_state.data, data_filtered= st.session_state.data_filtered)

    if 'data' in st.session_state:
        with col2:
            with st.container():
                st.subheader("Transverse Profile")
                id_ = st.number_input("Transverse profile", min_value=idmin, max_value=idmax, step = 1)
                scanData_v1 = transExtrac(segData = st.session_state.data, id=id_, max_val = st.session_state.height_max)
                # View and download data
                st.download_button(label="Download transverse profile", data=scanData_v1.to_csv().encode('utf-8'), file_name="transProfile_seg_" +str(segID)+"_scan_"+str(id_)+".csv", mime = "csv")

            with st.container():
                st.subheader("Longitudinal Profile")
                id_x = st.number_input("Longitudinal profile", min_value=0, max_value=1536,value=0, step = 1)

                # Extract transverse profile
                scanData_v2 = lonExtrac(segData = st.session_state.data, id=id_x, max_val = st.session_state.height_max)
                
                # View and download data
                st.download_button(label="Download longitudinal profile", data=scanData_v2.to_csv().encode('utf-8'), file_name="lonProfile_" +str(id_x)+"_"+ str(idmin) +" to " + str(idmax)+ ".csv", mime = "csv")

    
    
