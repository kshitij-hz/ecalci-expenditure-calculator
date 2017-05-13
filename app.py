#from flask import Flask, render_template, request, session, redirect, url_for		
from flask import *
from pymongo import MongoClient
from flask_mail import Mail, Message
from werkzeug import generate_password_hash, check_password_hash
from bson.objectid import ObjectId

app = Flask(__name__)
mail=Mail(app)
app.secret_key = 'any key string'
DEBUG=True
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'abc@gmail.com'
app.config['MAIL_PASSWORD'] = '*******'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)

connection = MongoClient('ds123455.mlab.com', 23456)
db = connection['dbname']
db.authenticate('username', 'password')


@app.route("/sendmail")
def sendmail():
   msg = Message('Hello', sender = 'club.technocrats.core@gmail.com', recipients = ['kshitij.hz@gmail.com'])
   msg.body = "Hello Flask message sent from Flask-Mail"
   mail.send(msg)
   return "Sent"


@app.route('/')
def index():
    if session.get('id'):
        return redirect('/home')
    return render_template('index.html')

@app.route('/home')
def home():
    if session.get('id'):
    	user = db.users.find_one({'_id':ObjectId(session['id'])})
    	groups = db.groups.find({'user': session['id']})
    	return render_template('home.html', user=user, groups=groups)
    redirect('/')
    	
@app.route('/eDelete/<group>/<id>')
def eDelete(group,id):
    if not session.get('id'):
    	redirect('/')
    result = db.expenditures.delete_one({'_id':ObjectId(id)})
    return redirect('/group/'+group)


@app.route('/logout')
def logout():
    # remove the id from the session if it is there
    session.pop('id', None)
    session.pop('name', None)
    return redirect(url_for('index'))

@app.route('/signup', methods = ['GET', 'POST'])
def showSignUp():	
	if session.get('id'):
		return redirect('/home')

	if request.method == 'POST':
	    i = request.form
	    if(db.users.count({'email':i['email']})):
	    	flash("User already registered !!")
	    else:
		    salt = 'qa3'
		    password = i['password']+salt
		    password = generate_password_hash(password)
		    data = {
		    	'name' : i['name'],
		    	'email' : i['email'],
		    	'password' : password
		    }
		    result = db.users.insert_one(data)
		    if(result):
		    	flash("Signed up successfully !!")
		    else:
		    	flash("Sign up failed, pls try again !!")	
	return render_template('signup.html')

@app.route('/newMember', methods = ['POST'])
def newMember():	
    if not session.get('id'):
        return redirect('/')
    i = request.form
    data = {
    	'group' : i['group'],
    	'member' : i['member']
    }
    result = db.members.insert_one(data)
    return redirect('/group/'+i['group'])

@app.route('/newGroup', methods = ['POST'])
def newGroup():
	if not session.get('id'):
		return redirect('/')

	i = request.form
	data = {
    	'user' : session['id'],
    	'group' : i['group']
    }
	result = db.groups.insert_one(data)
	return redirect('/home')

@app.route('/expenditure', methods = ['POST'])
def expenditure():	
    if not session.get('id'):
        return redirect('/')
    i = request.form
    group = i['group']
    amount = i['amount']
    members = db.members.find({'group':group})
    data = {}
    data['group'] = group 	
    data['title'] = i['title'] 	
    data['amount'] = amount 	
    for member in members:
    	data['e'+str(member.get('_id'))] = i['e'+str(member.get('_id'))]
    	data['p'+str(member.get('_id'))] = i['p'+str(member.get('_id'))]
    json_data = json.dumps(data)
    print(json_data)
    result = db.expenditures.insert_one(data)	
    return redirect('/group/'+group)

@app.route('/calculate/<group>')
def calculate(group):
	if not session.get('id'):
		return redirect('/')

	members = list(db.members.find({'group':group}))
	expenditures = db.expenditures.find({'group':group})
	group = db.groups.find_one({'_id':ObjectId(group)})
	data = {}
	total = 0
	for member in members:

	    data['te'+str(member.get('_id'))] = 0
	    data['tp'+str(member.get('_id'))] = 0

	for expenditure in expenditures:
		if(expenditure.get('amount')):
			total+=int(expenditure.get('amount'))
		else:
			total+=0;

		for member in members:
			data['te'+str(member.get('_id'))]+=int(expenditure.get('e'+str(member.get('_id')),'0'))
			data['tp'+str(member.get('_id'))]+=int(expenditure.get('p'+str(member.get('_id')),'0'))
	    
    #print(data)
	data2 = {}
	data3 = []

	for member in members:
		data2[str(member.get('_id'))] = data['tp'+str(member.get('_id'))] - data['te'+str(member.get('_id'))]
		data3.append({"member":str(member.get('_id')), "balance":data2[str(member.get('_id'))], "name": str(member.get('member'))}) 
    
	sorted_data = sorted(data3, key=lambda k: k['balance'])
	good, bad = [], []
	for x in sorted_data:
		(bad, good)[x.get('balance')>0].append(x)
	bad = list(reversed(bad))
    
	logs = []	    
	while bad:
		if abs(int(bad[0].get('balance')))<=int(good[0].get('balance')):
			logs.append(str(bad[0].get('name'))+' gives '+str(abs(bad[0].get('balance')))+' to '+str(good[0].get('name')))
			good[0] = {"member": good[0].get('member'), "balance": int(good[0].get('balance'))+bad[0].get('balance'), "name":good[0].get('name')}
			del bad[0]
			if(int(good[0].get('balance'))==0):
				del(good[0])
		else:
			logs.append(str(bad[0].get('name'))+' gives '+str(good[0].get('balance'))+' to '+str(good[0].get('name')))
			bad[0] = {"member": bad[0].get('member'), "balance": int(good[0].get('balance'))+bad[0].get('balance'), "name":bad[0].get('name')}
			del good[0]
			if(int(bad[0].get('balance'))==0):
				del(bad[0])
	return render_template('calculate.html',logs=logs, name=session['name'], group=group, data=data, data2=data2, members=members)


@app.route('/group/<id>')
def group(id):	
    if not session.get('id'):
    	redirect('/')
    group = db.groups.find_one({'_id':ObjectId(id)})
    members = db.members.find({'group':id})
    expenditures = db.expenditures.find({'group':id})
    return render_template('group.html',name=session['name'],group=group,members=list(members),expenditures=list(expenditures))

@app.route('/login', methods = ['GET', 'POST'])
def login():
   	if session.get('id'):
   		redirect('/home')
   	if request.method == 'POST':
   		i = request.form
   		salt = 'qa3'
   		password = i['password']+salt
   		dpass = db.users.find_one({'email':i['email']}) 
   		if(check_password_hash(dpass.get('password'),password)):
   			session['id'] = str(dpass.get('_id'))
   			session['name'] = dpass.get('name')
   			return redirect('/home')
   		else:
   			flash("Wrong username/password !!")
   	return render_template('login.html')


if __name__=="__main__":
    app.run()
