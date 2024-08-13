from flask import Flask, request, jsonify, send_file, abort
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from sqlalchemy import func
import base64
from difflib import SequenceMatcher
from io import BytesIO

app = Flask(__name__)
CORS(app, origins=['http://localhost:3000', 'http://192.168.0.101'])

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:root@localhost/myem'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class EventImage(db.Model):
    __tablename__ = 'event_images'
    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(255), nullable=False)
    image = db.Column(db.LargeBinary, nullable=False)
  

# Create the table if it doesn't exist
with app.app_context():
    db.create_all()



@app.route('/upload', methods=['POST'])
def upload_file():
    if 'image' not in request.files or 'event_type' not in request.form:
        return jsonify({'error': 'No image or event type provided'}), 400

    image = request.files['image']
    event_type = request.form['event_type']


    if image.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    image_data = image.read()
    new_image = EventImage(event_type=event_type, image=image_data)
    db.session.add(new_image)
    db.session.commit()

    return jsonify({'message': 'Image uploaded successfully'}), 200

@app.route('/images', methods=['GET'])
def get_images():
    event_type = request.args.get('event_type')
    if not event_type:
        return jsonify({'error': 'event_type query parameter is required'}), 400

    print(f"Received event_type: {event_type}")  # Debugging print statement

    images = EventImage.query.filter_by(event_type=event_type).all()
    images_list = [{'id': image.id, 'image_data': base64.b64encode(image.image).decode('utf-8')} for image in images]

    print(f"Found {len(images)} images for event_type {event_type}")  # Debugging print statement

    return jsonify({'images': images_list})




@app.route('/images/<int:image_id>', methods=['GET'])
def get_image(image_id):
    image = EventImage.query.get(image_id)
    if not image:
        return abort(404)

    return send_file(BytesIO(image.image), mimetype='image/jpeg')



class Bookings(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    address = db.Column(db.String(200), nullable=False)
    mobile = db.Column(db.String(20), nullable=False)
    alt_mobile = db.Column(db.String(20))
    event_type = db.Column(db.String(50), nullable=False)
    event_place = db.Column(db.String(100), nullable=False)
    event_date = db.Column(db.String(20), nullable=False)
    image = db.Column(db.LargeBinary, nullable=False)
    package = db.Column(db.String(50), nullable=True) 
    agent_name = db.Column(db.String(100), nullable=True)  
    booking_status = db.Column(db.String(50), nullable=True)
    negotiated_amount = db.Column(db.Float, nullable=True)
    event_status = db.Column(db.String(50), nullable=True)
    payment_status = db.Column(db.String(50), nullable=True)
    payment_proof = db.Column(db.LargeBinary, nullable=True)

class AgentOnboarding(db.Model):
    __tablename__ = 'agent_onboarding'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email_address = db.Column(db.String(100), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    fathers_name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    profession = db.Column(db.String(50), nullable=False)
    full_address = db.Column(db.String(255), nullable=False)
    desired_password = db.Column(db.String(100), nullable=False)
    profile_photo = db.Column(db.LargeBinary)
    aadhar_card = db.Column(db.LargeBinary)
    pan_card = db.Column(db.LargeBinary)
    other_govt_id = db.Column(db.LargeBinary)



@app.route('/book_call', methods=['POST', 'OPTIONS'])
def book_call():
    if request.method == 'OPTIONS':
        return '', 200

    data = request.json

    try:
        # Check if image data and task_id are provided
        image_data = None
        if 'image' in data and data['image']:
            image_data = base64.b64decode(data['image'])
        
        task_id = data.get('task_id')
        if not task_id:
            return jsonify({'error': 'Task ID is required'}), 400

        # Find the task by ID
        booking = Bookings.query.filter_by(id=task_id).first()
        if not booking:
            return jsonify({'error': 'Task not found'}), 404

        # Update the booking's image
        booking.image = image_data
        
        db.session.commit()
        
        print(f"Booking updated: {booking}")
        
        return jsonify({"message": "Booking updated successfully!"}), 200

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500




@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email_address = data.get('email')
    desired_password = data.get('password')

    agent = AgentOnboarding.query.filter_by(email_address=email_address, desired_password=desired_password).first()

    if agent:
        return jsonify({'message': 'Login successful!'}), 200
    else:
        return jsonify({'error': 'Invalid email or password'}), 401


@app.route('/agent_profile', methods=['GET'])
def get_agent_profile():
    email = request.args.get('email')
    if not email:
        return jsonify({'error': 'Email parameter is required'}), 400

    try:
        agent = AgentOnboarding.query.filter_by(email_address=email).first()
        if agent:
            profile_photo_base64 = base64.b64encode(agent.profile_photo).decode('utf-8') if agent.profile_photo else None
            return jsonify({
                'profile_photo': profile_photo_base64,
                'full_name': agent.full_name
            }), 200
        else:
            return jsonify({'error': 'Agent not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/tasks', methods=['GET'])
def get_tasks():
    email_address = request.args.get('email')
    if not email_address:
        return jsonify({'error': 'Email is required'}), 400

    agent = AgentOnboarding.query.filter_by(email_address=email_address).first()
    if not agent:
        return jsonify({'error': 'Agent not found'}), 404

    # Fetch all bookings and print for debugging
    all_bookings = Bookings.query.all()
    for booking in all_bookings:
        print(f"Booking ID: {booking.id}, Agent Name: {booking.agent_name}")

    # Perform a case-insensitive and partial match
    tasks = Bookings.query.filter(Bookings.agent_name.like(f"%{agent.full_name}%")).all()

    # Debug: print the number of fetched records
    print(f"Fetched {len(tasks)} records for agent {agent.full_name}")

    if not tasks:
        # Perform address matching
        agent_address = agent.full_address
        best_match = None
        best_match_score = 0
        for booking in all_bookings:
            match_score = SequenceMatcher(None, agent_address, booking.address).ratio()
            if match_score > best_match_score:
                best_match_score = match_score
                best_match = booking

        if best_match_score > 0.5:  # Assuming a threshold of 0.5 for a good match
            tasks = [best_match]
        else:
            return jsonify({'error': 'No matching tasks found'}), 404

    tasks_data = _get_task_details(tasks)
    
    return jsonify({'tasks': tasks_data}), 200

def _get_task_details(bookings):
    tasks_data = []
    for task in bookings:
        event_image = EventImage.query.filter_by(event_type=task.event_type).first()
        task_info = {
            'id': task.id,
            'name': task.name,
            'age': task.age,
            'address': task.address,
            'mobile': task.mobile,
            'alt_mobile': task.alt_mobile,
            'event_type': task.event_type,
            'event_place': task.event_place,
            'event_date': task.event_date,
            'package': task.package or '--',
            'image_data': base64.b64encode(task.image).decode('utf-8') if task.image else None,
            'booking_status': task.booking_status or '--',
            'negotiated_amount': task.negotiated_amount if task.negotiated_amount is not None else '--',
            'event_status': task.event_status or '--',
            'payment_status': task.payment_status or '--',
            'payment_proof': base64.b64encode(task.payment_proof).decode('utf-8') if task.payment_proof else None
        }
        tasks_data.append(task_info)
    return tasks_data

@app.route('/update_task', methods=['POST'])
def update_task():
    data = request.json
    task_id = data.get('id')
    package=data.get('package')
    booking_status = data.get('booking_status')
    negotiated_amount = data.get('negotiated_amount')
    event_status = data.get('event_status')
    payment_status = data.get('payment_status')
    payment_proof = data.get('payment_proof')

    # Get the file from the request, if any
    proof_file = request.files.get('proof')

    task = Bookings.query.get(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404

    # Set values to None if they are empty strings
    if booking_status == "":
        booking_status = None
    if negotiated_amount == "":
        negotiated_amount = None
    if event_status == "":
        event_status = None
    if payment_status == "":
        payment_status = None
    if payment_proof == "":
        payment_proof = None
    if package == "":
        package=None

    # Update the task fields if they are not None
    if package is not None:
        task.package = package
    if booking_status is not None:
        task.booking_status = booking_status
    else:
        task.booking_status = None
    if negotiated_amount is not None:
        task.negotiated_amount = negotiated_amount
    else:
        task.negotiated_amount = None
    if event_status is not None:
        task.event_status = event_status
    else:
        task.event_status = None
    if payment_status is not None:
        task.payment_status = payment_status
    else:
        task.payment_status = None

    # Update payment proof if provided
    if payment_proof is not None:
        task.payment_proof = base64.b64decode(payment_proof)
    elif proof_file:
        task.payment_proof = proof_file.read()

    db.session.commit()
    return jsonify({'message': 'Task updated successfully'}), 200




@app.route('/agents', methods=['GET'])
def get_agents():
    agents = AgentOnboarding.query.all()
    agents_data = [
        {
            'id': agent.id,
            'email_address': agent.email_address,
            'full_name': agent.full_name,
            'fathers_name': agent.fathers_name,
            'age': agent.age,
            'profession': agent.profession,
            'full_address': agent.full_address,
            'desired_password': agent.desired_password,
            'profile_photo': base64.b64encode(agent.profile_photo).decode('utf-8') if agent.profile_photo else None,
            'aadhar_card': base64.b64encode(agent.aadhar_card).decode('utf-8') if agent.aadhar_card else None,
            'pan_card': base64.b64encode(agent.pan_card).decode('utf-8') if agent.pan_card else None,
            'other_govt_id': base64.b64encode(agent.other_govt_id).decode('utf-8') if agent.other_govt_id else None
        }
        for agent in agents
    ]
    return jsonify({'agents': agents_data}), 200




class Gallery(db.Model):
    __tablename__ = 'our_gallery'
    id = db.Column(db.Integer, primary_key=True)
    image = db.Column(db.LargeBinary, nullable=False)
    description = db.Column(db.String(255), nullable=True)


@app.route('/gallery', methods=['POST'])
def update_gallery():
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400

    image = request.files['image']
    description = request.form.get('description', '')

    if image.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    image_data = image.read()
    new_gallery_item = Gallery(image=image_data, description=description)
    db.session.add(new_gallery_item)
    db.session.commit()

    return jsonify({'message': 'Image uploaded successfully'}), 200

@app.route('/gallery', methods=['GET'])
def get_gallery():
    images = Gallery.query.all()
    images_list = [{'id': img.id, 'image_data': base64.b64encode(img.image).decode('utf-8'), 'description': img.description} for img in images]

    return jsonify({'images': images_list})



class Review(db.Model):
    __tablename__ = 'reviews'  # Define the table name explicitly
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    event_type = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image = db.Column(db.LargeBinary)
    rating = db.Column(db.Integer, nullable=False)


@app.route('/reviews', methods=['POST'])
def add_review():
    if request.content_type.startswith('multipart/form-data'):
        name = request.form['name']
        event_type = request.form['event_type']
        description = request.form['description']
        rating = request.form['rating']
        image = request.files['image'].read() if 'image' in request.files else None

        new_review = Review(
            name=name,
            event_type=event_type,
            description=description,
            rating=rating,
            image=image
        )
        db.session.add(new_review)
        db.session.commit()
        return jsonify({'message': 'Review added successfully'}), 200
    else:
        return jsonify({'error': 'Unsupported Media Type'}), 415

@app.route('/reviews', methods=['GET'])
def get_reviews():
    reviews = Review.query.all()
    result = []
    for review in reviews:
        result.append({
            'id': review.id,
            'name': review.name,
            'event_type': review.event_type,
            'description': review.description,
            'image': base64.b64encode(review.image).decode('utf-8') if review.image else None,
            'rating': review.rating
        })
    return jsonify({'reviews': result}), 200



class Partner(db.Model):
    __tablename__ = 'partners'
    id = db.Column(db.Integer, primary_key=True)
    partner_name = db.Column(db.String(255), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    experience = db.Column(db.Integer, nullable=False)
    department = db.Column(db.String(255), nullable=False)
    pic = db.Column(db.LargeBinary)
    address = db.Column(db.Text)

    def to_dict(self):
     pic_base64 = base64.b64encode(self.pic).decode('utf-8') if self.pic else None
     return {
        'id': self.id,
        'partner_name': self.partner_name,
        'age': self.age,
        'experience': self.experience,
        'department': self.department,
        'pic': pic_base64,  # Encode image data to base64
        'address': self.address
    }




@app.route('/partners', methods=['GET'])
def get_partners():
    department = request.args.get('department')
    if department:
        partners = Partner.query.filter_by(department=department).all()
    else:
        partners = Partner.query.all()

    return jsonify([partner.to_dict() for partner in partners])


@app.route('/partners', methods=['POST'])
def add_partner():
    partner_name = request.form['partner_name']
    age = request.form['age']
    experience = request.form['experience']
    department = request.form['department']
    address = request.form['address']
    pic = request.files['pic'].read() if 'pic' in request.files else None

    new_partner = Partner(
        partner_name=partner_name,
        age=age,
        experience=experience,
        department=department,
        pic=pic,
        address=address
    )
    db.session.add(new_partner)
    db.session.commit()
    return jsonify(new_partner.to_dict()), 201


if __name__ == '__main__':
    app.run(debug=True)
