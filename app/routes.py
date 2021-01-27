# routes.py

from flask import session, render_template, flash, redirect, url_for, request, jsonify, json, make_response, after_this_request
#from flask_weasyprint import HTML, render_pdf
import pdfkit


from flask_bootstrap import Bootstrap
from werkzeug.urls import url_parse
from app.models import ShopName, Member, MemberActivity, MonitorSchedule, MonitorScheduleTransaction,\
MonitorWeekNote, CoordinatorsSchedule, ControlVariables, DuesPaidYears, Contact
from app import app
from app import db
from sqlalchemy import func, case, desc, extract, select, update, text
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, DBAPIError
from sqlalchemy.orm import aliased

import datetime as dt
from datetime import date, datetime, timedelta

import os.path
from os import path


from flask_mail import Mail, Message
mail=Mail(app)

@app.route('/')
@app.route('/index/')
@app.route('/index', methods=['GET'])
def index():

    # BUILD ARRAY OF NAMES FOR DROPDOWN LIST OF COORDINATORS
    # coordNames=[]
    # sqlNames = "SELECT Last_Name + ', ' + First_Name as coordName, Member_ID as coordID FROM tblMember_Data "
    # sqlNames += "WHERE Monitor_Coordinator = 1 "
    # sqlNames += "ORDER BY Last_Name, First_Name "
    # coordNames = db.engine.execute(sqlNames)
   
    # BUILD ARRAY OF MONITOR WEEKS FOR BOTH LOCATIONS
    # sqlWeeks = "SELECT Shop_Number as shopNumber, Start_Date,format(Start_Date,'MMM d, yyyy') as DisplayDate, "
    # sqlWeeks += "Coordinator_ID as coordID, Last_Name + ', ' + First_Name as coordName, eMail as coordEmail "
    # sqlWeeks += " FROM coordinatorsSchedule "
    # sqlWeeks += "LEFT JOIN tblMember_Data ON coordinatorsSchedule.Coordinator_ID = tblMember_Data.Member_ID "
    # sqlWeeks += "WHERE Start_Date >= getdate() "
    # sqlWeeks += "ORDER BY Shop_Number, Start_Date"
    # weeks = db.engine.execute(sqlWeeks)

    # MEMBER NAMES AND ID
    #sqlMembers = "SELECT Last_Name + ', ' + First_Name + ' (' + Member_ID + ')' as name FROM tblMember_Data "
    #sqlMembers += "ORDER BY Last_Name, First_Name "
    #nameList = db.engine.execute(sqlMembers)
    # BUILD ARRAY OF NAMES FOR DROPDOWN LIST OF MEMBERS
    nameArray=[]
    sqlSelect = "SELECT Last_Name, First_Name, Member_ID FROM tblMember_Data "
    sqlSelect += "ORDER BY Last_Name, First_Name "
    nameList = db.engine.execute(sqlSelect)
    position = 0
    for n in nameList:
        position += 1
        lastFirst = n.Last_Name + ', ' + n.First_Name + ' (' + n.Member_ID + ')'
        nameArray.append(lastFirst)
    
    # GET OPEN SECTIONS
    # NOT FULL, NOT CLOSED
    openSections = []
    return render_template("index.html",nameList=nameArray,openSections=openSections)
   

#PRINT PRESIDENTS REPORT
@app.route("/prtPresidentsReport", methods = ['GET'])
def prtPresidentsReport():
    destination = request.args.get('destination')  # destination is 'PRINT or 'PDF'
    
    # RETRIEVE TODAY'S DATE
    todays_date = date.today()
    todays_dateSTR = todays_date.strftime('%-m-%-d-%Y')

    # COMPUTE VALUES
    curYear = db.session.query(ControlVariables.Current_Dues_Year).filter(ControlVariables.Shop_Number == 1).scalar()
    pastYear = int(curYear) -1
   
    curYrPd = db.session.query(func.count(Member.Member_ID)).filter(Member.Dues_Paid == True).scalar()

    curYrNewMbrs = db.session.query(func.count(Member.Member_ID)).filter(extract('year',Member.Date_Joined)  == curYear).scalar()
    
    mbrsNotCertified = db.session.query(func.count(Member.Member_ID)).filter(Member.Certified != True).filter(Member.Dues_Paid == True).scalar()
   
    curYrInactive = db.session.query(func.count(Member.Member_ID)).filter(extract('year',Member.Inactive_Date)  == curYear).scalar()
    
    pastYrPaid = db.session.query(func.count(DuesPaidYears.Member_ID)).filter(DuesPaidYears.Dues_Year_Paid == pastYear).scalar()
    
    pastYrInactive = db.session.query(func.count(Member.Member_ID)).filter(extract('year',Member.Inactive_Date)  == 2019).scalar()
    
    
    # SQL QUERY TO COMPUTE THOSE PAID LAST YEAR, NOT PAID THIS YEAR
    sqlCompute = """SELECT tblDues_Paid_Years.Member_ID, tblDues_Paid_Years.Dues_Year_Paid
        FROM tblDues_Paid_Years
        WHERE (((tblDues_Paid_Years.Member_ID) Not In (Select Member_ID from tblDues_Paid_Years where Dues_Year_Paid = '2019')) 
        AND ((tblDues_Paid_Years.Dues_Year_Paid)='2020'))"""
    records = db.engine.execute(sqlCompute)
    pdPastNotCur = 0
    for r in records:
        pdPastNotCur += 1

    pastYrNewMbrs = db.session.query(func.count(Member.Member_ID)).filter(extract('year',Member.Date_Joined)  == pastYear).scalar()
    
    volunteers = db.session.query(func.count(Member.Member_ID)).filter(Member.NonMember_Volunteer == True).scalar()

    recordsInDB = db.session.query(func.count(Member.Member_ID)).scalar()
    
    return render_template("rptPresident.html",todaysDate=todays_dateSTR,curYear=curYear,pastYear=pastYear,\
    curYrPd=curYrPd,curYrNewMbrs=curYrNewMbrs,mbrsNotCertified=mbrsNotCertified,curYrInactive=curYrInactive,\
    pastYrPaid=pastYrPaid,pastYrInactive=pastYrInactive,pdPastNotCur=pdPastNotCur,pastYrNewMbrs=pastYrNewMbrs,\
    volunteers=volunteers,recordsInDB=recordsInDB)
            
 
@app.route("/prtMentors", methods=["GET"])
def prtMentorsTable():
    destination = request.args.get('destination')
    todays_date = date.today()
    todays_dateSTR = todays_date.strftime('%-m-%-d-%Y')
         
    mentors = db.session.query(Member)\
        .filter(Member.Mentor == True)\
        .order_by(Member.Last_Name,Member.First_Name)\
        .all()
    mentorDict = []
    mentorItem = []
    recordCnt = 0
    for m in mentors:
        displayName = m.Last_Name + ', ' + m.First_Name 
        if m.Nickname != None:
            displayName += ' (' + m.Nickname + ')'
        
        if m.Cell_Phone == None:
            cellPhone = ''
        else:
            cellPhone = m.Cell_Phone
        
        if m.Home_Phone == None:
            homePhone = ''
        else:
            homePhone = m.Home_Phone

        mentorItem = {
            'name':displayName,
            'cellPhone':cellPhone,
            'homePhone':homePhone,
            'eMail':m.eMail
        }
        mentorDict.append(mentorItem)
        recordCnt += 1
    return render_template("rptMentors.html",todaysDate=todays_dateSTR,mentorDict=mentorDict,recordCnt=recordCnt)

@app.route("/prtContacts", methods=["GET"])
def prtContacts():
    destination = request.args.get('destination')
    todays_date = date.today()
    todays_dateSTR = todays_date.strftime('%-m-%-d-%Y')
          
    # GET LIST OF CONTACT GROUPS
    groups = db.session.query(func.count(Contact.Contact_Group).label('count'),Contact.Contact_Group).group_by(Contact.Contact_Group).all()
    # for g in groups:
    #     print (g.Contact_Group,g.count)


    sqlContacts = "SELECT Contact_Group, Position, "
    sqlContacts += "tblContact_List.Member_ID as MemberID, [Last_Name], [First_Name],[Middle_Name],Nickname, "
    sqlContacts += "eMail, Home_Phone, Cell_Phone, Expires "
    sqlContacts += "FROM tblContact_List "
    sqlContacts += "LEFT JOIN tblMember_Data ON tblContact_List.Member_ID = tblMember_Data.Member_ID "
    sqlContacts += "ORDER BY Contact_Group, Position, Last_Name, First_Name"

    contacts = db.engine.execute(sqlContacts)
   
    contactDict = []
    contactItem = []
    for c in contacts:
        contactGroup = c.Contact_Group
        position = c.Position
        displayName = c.Last_Name + ', ' + c.First_Name 
        if c.Nickname != None:
            displayName += ' (' + c.Nickname + ')'
        
        if c.Cell_Phone == None:
            cellPhone = ''
        else:
            cellPhone = c.Cell_Phone
        
        if c.Home_Phone == None:
            homePhone = ''
        else:
            homePhone = c.Home_Phone

        contactItem = {
            'contactGroup':contactGroup,
            'position':position,
            'name':displayName,
            'cellPhone':cellPhone,
            'homePhone':homePhone,
            'eMail':c.eMail
        }
        contactDict.append(contactItem)
    return render_template("rptContactList.html",todaysDate=todays_dateSTR,contactDict=contactDict,groups=groups)
 
           

#PRINT WEEKLY LIST OF CONTACTS FOR COORDINATOR
@app.route("/printWeeklyMonitorContacts", methods=['GET'])
def printWeeklyMonitorContacts():
    dateScheduled=request.args.get('date')
    shopNumber=request.args.get('shop')
    destination = request.args.get('destination')

    # GET LOCATION NAME FOR REPORT HEADING
    shopRecord = db.session.query(ShopName).filter(ShopName.Shop_Number==shopNumber).first()
    shopName = shopRecord.Shop_Name
    
    #  DETERMINE START OF WEEK DATE
    #  CONVERT TO DATE TYPE
    dateScheduledDat = datetime.strptime(dateScheduled,'%Y-%m-%d')
    dayOfWeek = dateScheduledDat.weekday()

    # GET BEGIN, END DATES FOR REPORT HEADING
    beginDateDAT = dateScheduledDat 
    beginDateSTR = beginDateDAT.strftime('%m-%d-%Y')

    endDateDAT = beginDateDAT + timedelta(days=6)
    endDateSTR = endDateDAT.strftime('%m-%d-%Y')

    weekOfHdg = beginDateDAT.strftime('%B %d, %Y')
    
    # RETRIEVE SCHEDULE FOR SPECIFIC WEEK
    todays_date = date.today()
    todays_dateSTR = todays_date.strftime('%-m-%-d-%Y')

    # VARIABLES FOR DUPLICATE NAME CHECK
    savedSMname=''
    savedTCname=''
    
    # BUILD SELECT STATEMENT TO RETRIEVE SM MEMBERS SCHEDULE FOR CURRENT YEAR FORWARD
    sqlSelectSM = "SELECT tblMember_Data.Member_ID as memberID, "
    sqlSelectSM += "First_Name + ' ' + Last_Name as displayName, "
    sqlSelectSM += "Last_Monitor_Training as trainingDate, DATEPART(year,Last_Monitor_Training) as trainingYear, "
    sqlSelectSM += "'N' as trainingNeeded,"
    sqlSelectSM += " format(Date_Scheduled,'M/d/yyyy') as DateScheduled, DATEPART(year,Date_Scheduled) as scheduleYear, "
    sqlSelectSM += "Duty, eMail, Home_Phone, Cell_Phone,tblMember_Data.Monitor_Duty_Waiver_Expiration_Date as waiver "
    sqlSelectSM += "FROM tblMember_Data "
    sqlSelectSM += "LEFT JOIN tblMonitor_Schedule ON tblMonitor_Schedule.Member_ID = tblMember_Data.Member_ID "
    sqlSelectSM += "WHERE Date_Scheduled between '" + beginDateSTR + "' and '" + endDateSTR + "' "
    sqlSelectSM += " and (tblMonitor_Schedule.Duty = 'Shop Monitor' or tblMonitor_Schedule.Duty = 'Tool Crib') "
    sqlSelectSM += " and tblMonitor_Schedule.Shop_Number = " + shopNumber 
    sqlSelectSM += "ORDER BY Duty, Last_Name, First_Name"
    monitors = db.engine.execute(sqlSelectSM)
    
    SMmonitors = []
    TCmonitors = []

    # STEP THROUGH RESULT SET, DETERMINE IF TRAINING IS NEEDED, BUILD 2D ARRAY (LIST WITHIN LIST)
    for m in monitors:
        # IS TRAINING NEEDED?
        if (m.waiver == None):  # if no waiver 
            if (m.trainingYear == None):  # if last training year is blank
                needsTraining = 'Y'
            else:
                intTrainingYear = int(m.trainingYear) +2  # int of last training year
                intScheduleYear = int(m.scheduleYear) # int of schedule year
                if (intTrainingYear <= intScheduleYear):
                    needsTraining = 'Y'
                else:
                    needsTraining = 'N'
        else:
            needsTraining = 'N'

        #   BUILD SHOP MONITOR ARRAYS
        #   PUT DATA INTO ROW OF ARRAY (SMnames or TCnames)

        #   Group - Shop Monitor; 
        if (m.Duty == 'Shop Monitor' and m.displayName != savedSMname):  # ELIMINATE DUPLICATE NAMES
            savedSMname = m.displayName
            SMmonitor = {'name':m.displayName,
                'trainingYear': m.trainingYear,
                'eMail': m.eMail,
                'homePhone':m.Home_Phone,
                'cellPhone':m.Cell_Phone,
                'needsTraining':needsTraining}
            if SMmonitor['trainingYear'] == None:
                SMmonitor['trainingYear'] = ''
            if SMmonitor['homePhone'] == None:
                SMmonitor['homePhone'] = ''
            if SMmonitor['cellPhone'] == None:
                SMmonitor['cellPhone'] = ''
            SMmonitors.append(SMmonitor)

        #   Group - Tool Crib;  
        if (m.Duty == 'Tool Crib' and m.displayName != savedTCname):    # ELIMINATE DUPLICATE NAMES
            savedTCname = m.displayName 
            TCmonitor = {'name':m.displayName,
                'trainingYear': m.trainingYear,
                'eMail': m.eMail,
                'homePhone':m.Home_Phone,
                'cellPhone':m.Cell_Phone,
                'needsTraining':needsTraining}
            if TCmonitor['trainingYear'] == None:
                TCmonitor['trainingYear'] = ''
            if TCmonitor['homePhone'] == None:
                TCmonitor['homePhone'] = ''
            if TCmonitor['cellPhone'] == None:
                TCmonitor['cellPhone'] = ''
            TCmonitors.append(TCmonitor)
            
    
    if (destination == 'PDF'):
        #html =  render_template("rptWeeklyMonitorSchedule.h
        html = render_template("rptWeeklyContacts.html",\
            beginDate=beginDateSTR,endDate=endDateSTR,todaysDate=todays_dateSTR,\
            locationName=shopName,\
            SMmonitors=SMmonitors,TCmonitors=TCmonitors
            )
        # DEFINE PATH TO USE TO STORE PDF
        currentWorkingDirectory = os.getcwd()
        pdfDirectoryPath = currentWorkingDirectory + "/app/static/pdf"
        filePath = pdfDirectoryPath + "/rptWeeklyContacts.pdf"
        options = { 
            "enable-local-file-access": None
        }
        pdfkit.from_string(html,filePath, options=options)
        return redirect(url_for('index'))
    else:
        return render_template("rptWeeklyContacts.html",\
            beginDate=beginDateSTR,endDate=endDateSTR,todaysDate=todays_dateSTR,\
            locationName=shopName,\
            SMmonitors=SMmonitors,TCmonitors=TCmonitors
            )
    
    
#PRINT MEMBER MONITOR SCHEDULE TRANSACTIONS AND NOTES
@app.route("/prtMonitorTransactions", methods=["GET"])
def prtMonitorTransactions():
    memberID=request.args.get('memberID')
    destination = request.args.get('destination')
    curYear = request.args.get('year')
    lastYear = int(curYear)-1

    # GET TODAYS DATE
    todays_date = date.today()
    #todaysDate = todays_date.strftime('%-m-%-d-%Y')
    displayDate = todays_date.strftime('%B %-d, %Y') 

    # GET MEMBER NAME
    member = db.session.query(Member).filter(Member.Member_ID == memberID).first()
    displayName = member.First_Name
    if (member.Nickname != None and member.Nickname != ''):
        displayName += ' (' + member.Nickname + ')'
    displayName += ' ' + member.Last_Name
    #print(displayName)

    # GET MONITOR SCHEDULE TRANSACTIONS
    transactions = db.session.query(MonitorScheduleTransaction)\
    .filter(MonitorScheduleTransaction.Member_ID == memberID)\
    .all()
    # .filter(MonitorScheduleTransaction.Date_Scheduled.year == curYear)\
    
    #for t in transactions:
    #   print (t.Member_ID, t.Date_Scheduled)
    transactionDict = []
    transactionItem = []
    for t in transactions:
        #strDateScheduled = str(t.Date_Scheduled.year)
        #print(type(strDateScheduled),strDateScheduled,type(curYear),curYear)
        if (str(t.Date_Scheduled.year) == curYear):
            #print('match')
            transDateTime = t.Transaction_Date.strftime('%m-%d-%Y %I:%M %p')
            transType = t.Transaction_Type
            scheduled = t.Date_Scheduled.strftime('%m-%d-%Y')
            shift = t.AM_PM
            duty = t.Duty
            staffID = t.Staff_ID
            staffInitials = db.session.query(Member.Initials).filter(Member.Member_ID == staffID).scalar()
            if staffInitials == None:
                staffInitials=''
            
            transactionItem = {
                'transDateTime':transDateTime,
                'transType':transType,
                'scheduledDate':scheduled,
                'shift':shift,
                'duty':duty,
                'staffInitials':staffInitials
            }
            transactionDict.append(transactionItem) 


    # BUILD SELECT STATEMENT TO RETRIEVE NOTES FOR SPECIFIED MEMBER
    notes = db.session.query(MonitorWeekNote)\
    .all()
    #.filter(MonitorWeekNote.Date_Of_Change.year == curYear or MonitorWeekNote.Date_Of_Change == pastYear)\
    if notes == None:
        flash("There are no notes for this member.")
    notesDict = []
    notesItem = []
    for n in notes:
        note = str(n.Schedule_Note)
        # print('......................')
        # print(note)
        # print('......................')
        
        if note.find(memberID) != -1\
        and (n.Date_Of_Change.year == curYear or n.Date_Of_Change.year == lastYear):
            #print('++++++++++++++++++++++++++++++++')
            #print(n.Author_ID,n.Date_Of_Change,n.Schedule_Note)
            initials = db.session.query(Member.Initials).filter(Member.Member_ID == n.Author_ID).scalar()
            
            notesItem = {
                'noteDateTime':n.Date_Of_Change.strftime('%m-%d-%Y %I:%M %p'),
                'noteText':n.Schedule_Note,
                'staffInitials':initials
            }
            notesDict.append(notesItem) 


    if (destination == 'PDF') : 
        html =  render_template("rptWeeklyNotes.html",\
            beginDate=beginDateSTR,endDate=endDateSTR,\
            locationName=shopName,notes=notes,weekOfHdg=weekOfHdg,\
            todaysDate=todaysDate
            )
        currentWorkingDirectory = os.getcwd()
        pdfDirectoryPath = currentWorkingDirectory + "/app/static/pdf"
        filePath = pdfDirectoryPath + "/rptWeeklyNotes.pdf"    
        options = {"enable-local-file-access": None}
        pdfkit.from_string(html,filePath, options=options)
        return redirect(url_for('index'))
    else:
        return render_template("rptMonitorTransactions.html",\
            transactionDict=transactionDict,\
            notesDict=notesDict,displayName=displayName,\
            displayDate=displayDate,memberID=memberID)
        

@app.route("/eMailCoordinator", methods=["GET","POST"])
def eMailCoordinator():
    print('... begin /eMailCoordinator')
    # THIS ROUTINE ONLY RETURNS THE EMAIL MESSAGE TO BE USED FOR COORDINATORS ONLY EMAILS
    # ___________________________________________________________________________________

   # LOOK UP MESSAGE TO BE USED FOR EMAILS TO COORDINATORS
    sqlEmailMsgs = "SELECT [Email Name] as eMailMsgName, [Email Message] as eMailMessage FROM tblEmail_Messages "
    sqlEmailMsgs += "WHERE [Email Name] = 'Email To Coordinators'"
    eMailMessages = db.engine.execute(sqlEmailMsgs)
    for e in eMailMessages:
        eMailMsg=e.eMailMessage

    return jsonify(eMailMsg=eMailMsg)

@app.route("/eMailCoordinatorAndMonitors", methods=["GET","POST"])
def eMailCoordinatorAndMonitors():
    # GET WEEKOF DATE
    weekOf = request.args.get('weekOf')
    shopNumber = request.args.get('shopNumber')

    weekOfDAT = datetime.strptime(weekOf,'%Y-%m-%d')
    beginDateDAT = weekOfDAT
    beginDateSTR = beginDateDAT.strftime('%m-%d-%Y')
    endDateDAT = beginDateDAT + timedelta(days=6)
    endDateSTR = endDateDAT.strftime('%m-%d-%Y')

    # RETURN COORDINBATOR AND MONITORS NAMES AND EMAIL ADDRESSES; COORDINATORS PHONE
    # BUILD SELECT STATEMENT TO RETRIEVE SM MEMBERS SCHEDULE FOR CURRENT YEAR FORWARD
    sqlMonitors = "SELECT tblMember_Data.Member_ID as memberID, "
    sqlMonitors += "First_Name + ' ' + Last_Name as displayName, eMail "
    sqlMonitors += "FROM tblMember_Data "
    sqlMonitors += "LEFT JOIN tblMonitor_Schedule ON tblMonitor_Schedule.Member_ID = tblMember_Data.Member_ID "
    sqlMonitors += "WHERE Date_Scheduled between '" + beginDateSTR + "' and '" + endDateSTR + "' "
    sqlMonitors += "ORDER BY Last_Name, First_Name"
   
    monitors = db.engine.execute(sqlMonitors)
    monitorDict = []
    monitorItem = []
    savedName = ''
    
    for m in monitors:
        monitorItem = {
            'name':m.displayName,
            'eMail': m.eMail} 
        
        if savedName != m.displayName :
            monitorDict.append(monitorItem)
        savedName = m.displayName

    # LOOK UP EMAIL MESSAGE FOR COORDINATOR
    sqlEmailMsgs = "SELECT [Email Name] as eMailMsgName, [Email Message] as eMailMessage FROM tblEmail_Messages "
    sqlEmailMsgs += "WHERE [Email Name] = 'Email To Coordinators'"
    eMailMessages = db.engine.execute(sqlEmailMsgs)
    for e in eMailMessages:
        eMailMsg=e.eMailMessage

    return jsonify(monitorDict=monitorDict,eMailMsg=eMailMsg)

@app.route("/getMembersEmailAddress", methods=["GET","POST"])
def getMembersEmailAddress():
    memberID=request.args.get('memberID')
    weekOf = request.args.get('weekOf')
    shopNumber = request.args.get('shopNumber')
    weekOfDat = datetime.strptime(weekOf,'%Y-%m-%d')
    displayDate = weekOfDat.strftime('%B %d, %Y') 

    # GET MEMBER'S EMAIL ADDRESS;
    eMail=db.session.query(Member.eMail).filter(Member.Member_ID == memberID).scalar()

    # LOOK UP EMAIL MESSAGE FOR MEMBER
    eMailMsg=db.session.query(EmailMessages.eMailMessage).filter(EmailMessages.eMailMsgName == 'Email To Members').scalar()
    
    return jsonify(eMail=eMail,eMailMsg=eMailMsg,curWeekDisplayDate=displayDate)


# THE FOLLOWING ROUTINE IS CALLED WHEN THE USER SELECTS A WEEK
@app.route("/getCoordinatorData", methods=["GET","POST"])
def getCoordinatorData():
    # GET WEEKOF DATE
    # RETURN COORDINATOR NAME, EMAIL, PHONE
    weekOf = request.args.get('weekOf')
    shopNumber = request.args.get('shopNumber')
    weekOfDat = datetime.strptime(weekOf,'%Y-%m-%d')
    displayDate = weekOfDat.strftime('%B %d, %Y')  #'%m/%d/%Y')

    # GET COORDINATOR ID FROM COORDINATOR TABLE
    coordinatorRecord = db.session.query(CoordinatorsSchedule)\
        .filter(CoordinatorsSchedule.Start_Date==weekOf)\
        .filter(CoordinatorsSchedule.Shop_Number==shopNumber).first()
    if coordinatorRecord == None:
        coordID= ''
        coordName = 'Not assigned.'
        coordEmail = ''
        coordPhone = ''
    else:
        # LOOK UP COORDINATORS NAME
        coordinatorID = coordinatorRecord.Coordinator_ID
        memberRecord = db.session.query(Member).filter(Member.Member_ID==coordinatorID).first()
        if memberRecord == None:
            coordID = ''
            coordName = 'Not assigned.'
            coordEmail = ''
            coordPhone = ''
        else:
            coordID = memberRecord.Member_ID
            coordName = memberRecord.First_Name + ' ' + memberRecord.Last_Name
            coordEmail = memberRecord.eMail
            coordPhone = memberRecord.Cell_Phone

    return jsonify(
        coordID=coordID,
        coordName=coordName,
        coordEmail=coordEmail,
        coordPhone=coordPhone,
        curWeekDisplayDate=displayDate
    )

@app.route("/sendEmail", methods=["GET","POST"])
def sendEmail():
    # DETERMINE PATH TO PDF FILES
    currentWorkingDirectory = os.getcwd()
    pdfDirectoryPath = currentWorkingDirectory + "/app/static/pdf"
    filePath = pdfDirectoryPath + "/printWeeklyMonitorSchedule.pdf"
   
    # GET RECIPIENT
    recipient = request.args.get('recipient')
    bcc=("Woodshop","villagesWoodShop@embarqmail.com")
    #cc=("Richard l. Hartley","hartl1r@gmail.com")
    # FOR TESTING PURPOSES ..............................
    recipient = ("Richard Hartley", "hartl1r@gmail.com")

    recipientList = []
    recipientList.append(recipient)
    subject = request.args.get('subject')
    message = request.args.get('message')
    msg = Message('Hello', sender = 'hartl1r@gmail.com', recipients = recipientList) #, bcc=bcc)
    msg.subject = subject
    msg.body = message

    # ADD ATTACHMENTS

    # DETERMINE PATH TO PDF FILES
    currentWorkingDirectory = os.getcwd()
    pdfDirectoryPath = currentWorkingDirectory + "/app/static/pdf"
    
    # CHECK FOR A SCHEDULE REPORT
    filePath = pdfDirectoryPath + "/rptWeeklyMonitorSchedule.pdf"
    if (path.exists(filePath)):
        with app.open_resource(filePath) as fp:
            msg.attach(filename="rptSchedule.pdf",disposition="attachment",content_type="application/pdf",data=fp.read())

    # CHECK FOR A CONTACTS REPORT
    filePath = pdfDirectoryPath + "/rptWeeklyContacts.pdf"
    if (path.exists(filePath)):
        with app.open_resource(filePath) as fp:
            msg.attach(filename="rptContacts.pdf",disposition="attachment",content_type="application/pdf",data=fp.read())

    # CHECK FOR A NOTES REPORT
    filePath = pdfDirectoryPath + "/rptWeeklyNotes.pdf"
    if (path.exists(filePath)):
        with app.open_resource(filePath) as fp:
            msg.attach(filename="rptNotes.pdf",disposition="attachment", content_type ="application/pdf",data=fp.read())

    # CHECK FOR A SUB LIST REPORT
    filePath = pdfDirectoryPath + "/rptSubList.pdf"
    if (path.exists(filePath)):  
        with app.open_resource(filePath) as fp:
            msg.attach(filename="rptSubList.pdf",disposition="attachment",content_type="application/pdf",data=fp.read())

    
    # SEND THE EMAIL
    mail.send(msg)
    RemovePDFfiles(pdfDirectoryPath)
    #flash ('Message sent.','SUCCESS')
    return redirect(url_for('index'))


def RemovePDFfiles(pdfDirectoryPath):
    # REMOVE PDF FILES
    
    filePath = pdfDirectoryPath + "/rptWeeklyMonitorSchedule.pdf"
    if (os.path.exists(filePath)):
        os.remove(filePath)
    
    filePath = pdfDirectoryPath + "/rptWeeklyContacts.pdf"
    if (os.path.exists(filePath)):
        os.remove(filePath)

    filePath = pdfDirectoryPath + "/rptWeeklyNotes.pdf"
    if (os.path.exists(filePath)):
        os.remove(filePath)

    filePath = pdfDirectoryPath + "/rptSubList.pdf"
    if (os.path.exists(filePath)):
        os.remove(filePath)

def TrainingNeeded(lastTrainingDate): 
    todays_date = date.today()
    todays_dateSTR = todays_date.strftime('%-m-%-d-%Y')
    thisYear = todays_date.strftime("%Y")
    lastAcceptableTrainingYear = int(thisYear) - 2
    
    if lastTrainingDate == None:
        return True
    
    try:
        lastTrainingYear = lastTrainingDate.strftime("%Y")
        if int(lastTrainingYear) <= lastAcceptableTrainingYear:
            return True
        else:
            return False
    except:
        print ('Error in TrainingNeeded routine using - ', lastTrainingDate)
        return True

