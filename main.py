# Modules
import pandas as pd
import pyrebase
import streamlit as st
import plotly.express as px
import numpy as np
from datetime import datetime
from wordcloud import WordCloud, STOPWORDS
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from collections import Iterable
from collections import Counter
import requests
import json
import time as t

# Configure page
st.set_page_config(
    page_title='DUTE 2022/2023',
    page_icon="👩‍💻",
    layout="wide",
    initial_sidebar_state="expanded"
)
# remove main menu and the footer
hide_menu_style = """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        </style>
    """
st.markdown(hide_menu_style, unsafe_allow_html=True)

# Configuration key
firebaseConfig = {
    'apiKey': st.secrets['apiKey'],
    'authDomain': st.secrets['authDomain'],
    'projectId': st.secrets['projectId'],
    'databaseURL': st.secrets['databaseURL'],
    'storageBucket': st.secrets['storageBucket'],
    'messagingSenderId': st.secrets['messagingSenderId'],
    'appId': st.secrets['appId'],
    'measurementId': st.secrets['measurementId']
}

# Firebase Authenticaiton
firebase = pyrebase.initialize_app(firebaseConfig)
auth = firebase.auth()

# Database
db = firebase.database()
storage = firebase.storage()

# Initialisation
bg_color = '#636EFA'  # "#856ff8"
start_day = datetime(2022, 10, 3)  # Mon of the week


def week_no():
    return int((datetime.today() - start_day).days / 7) + 1


# load data
pre_questions = pd.read_excel('input/survey_questions.xlsx', sheet_name='pre_survey')
post_questions = pd.read_excel('input/survey_questions.xlsx', sheet_name='post_survey')
learning_obj = pd.read_excel('input/survey_questions.xlsx', sheet_name='learning_objectives')

if "login_state" not in st.session_state:
    st.session_state.login_state = False


def main():
    st.title("DUTE 2022/2023")
    menu = ['Login', 'SignUp']
    # Authentication
    authen_section = st.sidebar.empty()
    choice = authen_section.selectbox("Menu", menu)

    if choice == 'Login':
        clear_signup()
        login_section = st.sidebar.container().empty()
        with login_section.container():
            email = st.text_input('Email address')  # no side bar is needed
            password = st.text_input('Password', type='password')
            reset = st.checkbox('Forget my password', key='reset_password')
            if reset:
                try:
                    auth.send_password_reset_email(email)
                    st.info("Email has been sent to: " + email +
                            ". Please check your email/junk mail and follow the instruction to reset the password.")
                except requests.exceptions.HTTPError as e:
                    error_json = e.args[1]
                    error = json.loads(error_json)['error']['message']
                    if error == "INVALID_EMAIL":
                        st.error("Email isn't correct. Please input the correct email.")
            login = st.button('Login')
        if login:
            try:
                user = auth.sign_in_with_email_and_password(email, password)
                st.session_state.user = user
                log('login', user)
                login = False
                st.session_state.login_state = True
            except requests.exceptions.HTTPError as e:
                error_json = e.args[1]
                error = json.loads(error_json)['error']['message']
                if error == "EMAIL_NOT_FOUND":
                    st.sidebar.error("Email wasn't found. Please sign up.")
                elif error == "INVALID_PASSWORD":
                    st.sidebar.error("Invalid password. Please enter the correct email/password.")
        # show info if login
        if st.session_state.login_state:
            user = st.session_state.user
            name = db.child('users').child(user['localId']).child("name").get().val()
            st.subheader("Welcome: " + name + " to Week " + str(week_no()))
            clear_login(authen_section, login_section)
            # generate menu
            pages = ['😃 My weekly goals/plans', '📮 Pre-survey Submission', '📊 Pre-survey Results',
                     '📮 Post-survey Submission', '📊 Post-survey Results']
            pages_holder = st.sidebar.empty()
            selected_page = pages_holder.selectbox("Menu", pages)
            st.sidebar.button("Log out", on_click=log_out, key="logout_btn")
            if selected_page == '😃 My weekly goals/plans':
                st.title('✦ My weekly goals/plans')
                log('see_homepage', user)
                pull_goals(user)
            elif selected_page == '📮 Pre-survey Submission':
                st.title('✦ Submit Pre-survey')
                log('see_submit_pre_survey_page', user)
                branchID = user['localId'] + "_" + str(week_no())
                pre_survey_db = db.child('pre-survey').child(branchID).get().val()
                if pre_survey_db is None:
                    st.warning("Please submit a pre-survey for this week.")
                else:
                    st.info("You've already submitted the pre-survey for this week. Submit again to overwrite the former survey.")
                with st.form('pre_survey', clear_on_submit=True):
                    response = pre_survey()
                    submitted = st.form_submit_button('Submit')
                    if submitted:
                        time = int(datetime.now().timestamp() * 1000)
                        db.child("pre-survey").child(branchID).child("id").set(user['localId'])
                        db.child("pre-survey").child(branchID).child("timestamp").set(time)
                        db.child("pre-survey").child(branchID).child("response").set(response)
                        log('submit_pre_survey', user)
                        info_box = st.empty()
                        with info_box:
                            st.success(
                                "Thank you very much! You've successfully submitted the pre-survey for this week.")
                            t.sleep(5)
                        info_box.empty()
            elif selected_page == '📊 Pre-survey Results':
                log('see_pre_survey_page', user)
                pull_results(user, 'pre')
            elif selected_page == '📮 Post-survey Submission':
                st.title('✦ Submit Post-survey')
                log('see_submit_post_survey_page', user)
                branchID = user['localId'] + "_" + str(week_no())
                post_survey_db = db.child('post-survey').child(branchID).get().val()
                if post_survey_db is None:
                    st.warning("Please submit a post-survey for this week.")
                else:
                    st.info("You've already submitted the post-survey for this week. Submit again to overwrite the former survey.")
                with st.form('post_survey', clear_on_submit=True):
                    response = post_survey()
                    submitted_post = st.form_submit_button('Submit')
                    if submitted_post:
                        time = int(datetime.now().timestamp() * 1000)
                        db.child("post-survey").child(branchID).child("id").set(user['localId'])
                        db.child("post-survey").child(branchID).child("timestamp").set(time)
                        db.child("post-survey").child(branchID).child("response").set(response)
                        log('submit_post_survey', user)
                        info_box = st.empty()
                        with info_box:
                            st.success(
                                "Thank you very much! You've successfully submitted the post-survey for this week.")
                            t.sleep(5)
                        info_box.empty()
            elif selected_page == '📊 Post-survey Results':
                log('see_post_survey_page', user)
                pull_results(user, 'post')

    elif choice == 'SignUp':
        st.subheader("Create new account")
        new_email = st.text_input('Email address', key='signup_email')
        new_password = st.text_input('Password', type='password', key='signup_password')
        name = st.text_input('Name', key='signup_name')  # value='default'
        group = st.selectbox('Group number', np.arange(1, 11), key='signup_group')
        submit = st.button('Create my account')
        if submit:
            try:  # push new user data in Firebase
                user = auth.create_user_with_email_and_password(new_email, new_password)
                db.child('users').child(user['localId']).child("id").set(user['localId'])
                db.child('users').child(user['localId']).child("name").set(name)
                db.child('users').child(user['localId']).child("email").set(new_email)
                db.child('users').child(user['localId']).child("group").set(str(group))
                log('signup', user)
                st.success('Your account is created successfully!')
                st.info('Please login via the drop down selection on the left.')
            except requests.exceptions.HTTPError as e:
                error_json = e.args[1]
                error = json.loads(error_json)['error']['message']
                if error == "EMAIL_EXISTS":
                    st.error("Email already exists. Please log in or sign up with the new email.")


def print_status():
    st.sidebar.write("session state:", st.session_state)
    st.sidebar.write("auth:", auth.current_user)


def log(action, user):
    data = {
        'timestamp': int(datetime.now().timestamp() * 1000),
        'activity': action,
        'id': user['localId']
    }
    result = db.child('activities').push(data, user['localId'])


def log_out():
    log('logout', st.session_state.user)
    st.session_state.user = None
    st.session_state.login_state = False
    st.success("You've logged out.")
    # print_status()


def clear_signup():
    st.session_state["signup_email"] = ""
    st.session_state["signup_password"] = ""
    st.session_state["signup_name"] = ""
    st.session_state["signup_group"] = '1'


def clear_login(authen_section, login_section):
    authen_section.empty()
    login_section.empty()
    # logout_btn = st.sidebar.button("Log out", on_click=log_out)


def pre_survey():
    response = {}
    theme = ""
    for ind, q in pre_questions.iterrows():
        item = 'q' + str(q['No'])
        if theme != q['Category']:
            st.markdown("### 📌 " + q['Category'])
            theme = q['Category']
        if q['ChoiceType'] == 'select_slider':
            response[item] = st.select_slider(q['Question'], q['Choice'].split(';'))
        elif q['ChoiceType'] == 'text_input':
            response[item] = st.text_input(q['Question'])
        elif q['ChoiceType'] == 'multiselect':
            response[item] = st.multiselect(q['Question'], q['Choice'].split(';'))
        elif q['ChoiceType'] == 'selectbox':
            response[item] = st.selectbox(q['Question'], learning_obj.loc[week_no() - 1, 'LearningObjective'].split(';'))
    return response


def post_survey():
    response = {}
    theme = ""
    for ind, q in post_questions.iterrows():
        item = 'q' + str(q['No'])
        if theme != q['Category']:
            st.markdown("### 📌 " + q['Category'])
            theme = q['Category']
        if q['ChoiceType'] == 'select_slider':
            response[item] = st.select_slider(q['Question'], q['Choice'].split(';'))
        elif q['ChoiceType'] == 'text_input':
            response[item] = st.text_input(q['Question'])
        elif q['ChoiceType'] == 'multiselect':  # this can be null and no field at all
            temp = st.multiselect(q['Question'], q['Choice'].split(';'))
            response[item] = temp if temp != [] else ""
    return response


def pull_results(user, survey_type):
    # fetch user data
    users_db = db.child('users').get().val()
    users = pd.DataFrame.from_dict(users_db, orient='index')
    group = users.loc[users['id'] == user['localId'], 'group'].values[0]

    # show options
    if 'pre_week' not in st.session_state:
        st.session_state.pre_week = week_no()
    if 'post_week' not in st.session_state:
        st.session_state.post_week = week_no()
    key_name = survey_type + '-results'
    selected_week = st.selectbox("Please select a week to see the group results:", np.arange(1, week_no() + 1),
                                 index=week_no() - 1, key=key_name)
    if survey_type == 'pre' and selected_week != st.session_state.pre_week:
        log("select_pre_survey_week_" + str(selected_week), user)
        st.session_state.pre_week = selected_week
    if survey_type == 'post' and selected_week != st.session_state.post_week:
        log("select_post_survey_week_" + str(selected_week), user)
        st.session_state.post_week = selected_week
    weeks_ind = pd.date_range(start_day, periods=10, freq='W-MON')
    # st.write("Select from this day:" + str(weeks_ind[selected_week-1]) + "to before this day:"+ str(weeks_ind[selected_week]))

    # fetch survey db
    if survey_type == 'pre':
        survey_db = db.child('pre-survey').get().val()
        questions = pre_questions
    elif survey_type == 'post':
        survey_db = db.child('post-survey').get().val()
        questions = post_questions

    # prep data for display
    if survey_db is not None:
        survey = pd.DataFrame.from_dict(survey_db, orient='index')
        survey_data = survey.merge(users[["id", "group"]], on="id", how="left")
        survey_data["date"] = survey_data['timestamp'].apply(lambda x: datetime.fromtimestamp(x / 1000))
    else:
        survey_data = None

    num_survey = 0
    if survey_data is not None:
        survey_data = survey_data[(survey_data["group"] == group) &
                                  (survey_data['date'] >= weeks_ind[selected_week - 1]) &
                                  (survey_data['date'] < weeks_ind[selected_week])]
        num_survey = len(survey_data)
    if survey_type == 'pre':
        st.title("✦ Pre-survey results of Group: " + group + " | No. of responses: " + str(num_survey))
    else:
        st.title("✦ Post-survey results of Group: " + group + " | No. of responses: " + str(num_survey))

    # visualise results
    if survey_data is None:#survey_data.empty:
        st.write("No response in the selected period.")
    else:
        results = pd.DataFrame()
        for key, val in survey_data.response.items():
            temp = pd.DataFrame.from_dict(val, orient='index')  # individual response
            # results = results.append(temp.T, ignore_index=True) #depreciated
            results = pd.concat([results, temp.T])

        # show result
        if not results.empty:
            theme = ""
            for ind, q in questions.iterrows():
                item = 'q' + str(q['No'])
                # print category title
                if theme != q['ShortQuestion']:
                    st.markdown("### 📌 " + q['ShortQuestion'])
                    theme = q['ShortQuestion']
                st.markdown("> " + q['Question'])

                # show visualisation
                if q['Chart'] == 'bar':  # bar chart
                    data = results[item].value_counts().reindex(q['Choice'].split(';')).reset_index(level=0)
                    data.insert(loc=0, column='Rank', value=np.arange(len(data)) + 1)
                    data = data.rename({'index': q['ShortQuestion'], item: 'Count'}, axis='columns')
                    if data is not None:
                        fig = px.bar(data, x=q['ShortQuestion'], y='Count')
                        fig.update_yaxes(visible=False, showticklabels=False)  # no y axis
                        fig.update_xaxes(title="")
                        fig.update_layout({'plot_bgcolor': 'rgba(0, 0, 0, 0)', 'paper_bgcolor': 'rgba(0, 0, 0, 0)',
                                           'font_size': 16})  # no bg
                        fig.update_traces(marker_line_width=0)  # no stroke
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.write("No data")
                elif q['Chart'] == 'pie':  # pie chart
                    data = results[item].value_counts().reset_index(level=0)
                    data.insert(loc=0, column='Rank', value=np.arange(len(data)) + 1)
                    data = data.rename({'index': q['ShortQuestion'], item: 'Count'}, axis='columns')
                    if data is not None:
                        fig = px.pie(data, values='Count', names=q['ShortQuestion'])
                        fig.update_layout(font_size=16)
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.write("No data")
                elif q['Chart'] == 'bar-h':  # for multi-selected questions, display horizontal bar
                    strategy_lists = list(flatten(results[item]))
                    data = pd.DataFrame.from_dict(Counter(strategy_lists), orient='index').reset_index(level=0)
                    data = data.rename({'index': q['ShortQuestion'], 0: 'Count'}, axis='columns').sort_values('Count',
                                                                                                              ascending=False)
                    if data is not None:
                        fig = px.bar(data, y=q['ShortQuestion'], x='Count', orientation='h')
                        fig.update_layout(
                            {'plot_bgcolor': 'rgba(0, 0, 0, 0)', 'paper_bgcolor': 'rgba(0, 0, 0, 0)'})  # no bg
                        fig.update_traces(marker_line_width=0)  # no stroke
                        fig.update_xaxes(visible=False, showticklabels=False)
                        # fig.update_yaxes(title="", categoryorder='total ascending')
                        fig.update_layout(font_size=16)
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.write("No data")
                elif q['Chart'] == 'wordcloud':
                    data = results[item]
                    text = ' '.join(filter(None, data))
                    if text == "":
                        c, c1, c2 = st.columns([0.1, 1, 2])
                        with c1:
                            st.write("No data")
                    else:
                        c, c1, c2 = st.columns([0.1, 1, 2])
                        with c1:
                            s = ''
                            for i in data:
                                if i != '':
                                    s += "- " + i + "\n"
                            st.markdown(s)
                        with c2:
                            try:
                                wordcloud = WordCloud(background_color=bg_color, colormap='Set3', stopwords=STOPWORDS,
                                                      random_state=1, collocations=False, mode='RGBA').generate(text)
                                fig, ax = plt.subplots(figsize=(12, 8))
                                fig.patch.set_visible(False)
                                plt.axis("off")
                                ax.imshow(wordcloud, interpolation='bilinear')
                                plt.show()
                                st.pyplot(fig)
                            except ValueError as ve:
                                st.error("No word cloud to show.")


def pull_goals(user):
    # fetch user data|pre:q5,q6|post:q19
    id = user['localId']

    # fetch pre-survey data
    start_week = start_day.isocalendar().week
    pre_survey_db = db.child('pre-survey').get().val()
    if pre_survey_db is not None:
        pre_surveys = pd.DataFrame.from_dict(pre_survey_db, orient='index')
        pre_surveys = pre_surveys[pre_surveys.id == id]
        if not pre_surveys.empty:
            pre_surveys['date'] = pre_surveys['timestamp'].apply(lambda x: datetime.fromtimestamp(x / 1000))#this is british time, not utc
            pre_surveys['week'] = pre_surveys['date'].dt.week - start_week + 1
            response = pd.json_normalize(pre_surveys.response)
            # construct new var for visualise
            my_data = pd.DataFrame()
            my_data['Week'] = pre_surveys.week.reset_index(drop=True)
            my_data['Pre-goals'] = response.q5
            my_data['Pre-plans'] = response.q6

    # fetch post-survey data
    post_survey_db = db.child('post-survey').get().val()
    if post_survey_db is not None:
        post_surveys = pd.DataFrame.from_dict(post_survey_db, orient='index')
        post_surveys = post_surveys[post_surveys.id == id]
        if not post_surveys.empty:
            post_surveys['date'] = post_surveys['timestamp'].apply(lambda x: datetime.fromtimestamp(x / 1000))
            post_surveys['week'] = post_surveys['date'].dt.week - start_week + 1
            response = pd.json_normalize(post_surveys.response)

            # construct new var for visualise
            my_data_post = pd.DataFrame()
            my_data_post['Week'] = post_surveys.week.reset_index(drop=True)
            my_data_post['Follow-up plans'] = response.q19

    # table_data = pd.DataFrame(columns=['Week', 'Pre-goals', 'Pre-plans', 'Follow-up plans'])
    if 'my_data' not in locals():
        my_data = pd.DataFrame({'Week': [week_no()], 'Pre-goals': ['No data'], 'Pre-plans': ['No data']})
    if 'my_data_post' not in locals():
        my_data_post = pd.DataFrame({'Week': [week_no()], 'Follow-up plans': ['No data']})

    all_data = pd.merge(my_data, my_data_post, on='Week', how='outer')
    all_data = all_data.fillna("-")
    fig = go.Figure(data=[go.Table(
        columnwidth=[0.8, 3, 4, 4],
        header=dict(values=all_data.columns,
                    # line_color='black',
                    fill_color=bg_color,  # 'Crimson'
                    line_width=0,
                    height=35,
                    align='left',
                    font=dict(color='white', size=16)),
        cells=dict(values=[all_data['Week'], all_data['Pre-goals'], all_data['Pre-plans'], all_data['Follow-up plans']],
                   # line_color='black',
                   align='left',
                   fill_color='#262730',  # 'rgb(30, 30, 30)',
                   height=50,
                   line_width=0,
                   font=dict(color='white', size=14)))])
    fig.update_layout(margin=dict(l=2, r=2, b=2, t=2))
    st.plotly_chart(fig, use_container_width=True)


def flatten(lis):
    for item in lis:
        if isinstance(item, Iterable) and not isinstance(item, str):
            for x in flatten(item):
                yield x
        else:
            yield item


if __name__ == "__main__":
    main()

### EXPANDER
# if 'is_expanded' not in st.session_state:
#     st.session_state['is_expanded'] = True
# container = st.expander("XXX", expanded=st.session_state['is_expanded'])
# with container:
#     [DO STUFF]
#     st.session_state['is_expanded'] = False
