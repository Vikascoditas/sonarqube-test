from flask import Flask, jsonify, request, abort
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
ma = Marshmallow(app)

# Constants
ITEM_NOT_FOUND = "Item not found"
MISSING_USERNAME_OR_PASSWORD = "Missing username or password"
INVALID_CREDENTIALS = "Invalid credentials"
MISSING_ITEM_NAME = "Missing item name"

# Database models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))

# Schemas
class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User

class ItemSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Item

# Home route
@app.route('/')
def home():
    return "Welcome to the Flask app!"

# User registration route
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        abort(400, description=MISSING_USERNAME_OR_PASSWORD)
    
    hashed_password = generate_password_hash(password)
    new_user = User(username=username, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify(message="User registered successfully"), 201

# User login route
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password, password):
        return jsonify(message="Login successful")
    else:
        abort(401, description=INVALID_CREDENTIALS)

# Get all items route
@app.route('/api/items', methods=['GET'])
def get_items():
    items = Item.query.all()
    item_schema = ItemSchema(many=True)
    return jsonify(item_schema.dump(items))

# Get item by ID route
@app.route('/api/items/<int:item_id>', methods=['GET'])
def get_item(item_id):
    item = Item.query.get(item_id)
    if item is None:
        abort(404, description=ITEM_NOT_FOUND)
    item_schema = ItemSchema()
    return jsonify(item_schema.dump(item))

# Create item route
@app.route('/api/items', methods=['POST'])
def create_item():
    data = request.json
    name = data.get('name')
    description = data.get('description')
    if not name:
        abort(400, description=MISSING_ITEM_NAME)
    
    new_item = Item(name=name, description=description)
    db.session.add(new_item)
    db.session.commit()
    
    item_schema = ItemSchema()
    return jsonify(item_schema.dump(new_item)), 201

# Update item route
@app.route('/api/items/<int:item_id>', methods=['PUT'])
def update_item(item_id):
    item = Item.query.get(item_id)
    if item is None:
        abort(404, description=ITEM_NOT_FOUND)
    
    data = request.json
    item.name = data.get('name', item.name)
    item.description = data.get('description', item.description)
    db.session.commit()
    
    item_schema = ItemSchema()
    return jsonify(item_schema.dump(item))

# Delete item route
@app.route('/api/items/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    item = Item.query.get(item_id)
    if item is None:
        abort(404, description=ITEM_NOT_FOUND)
    
    db.session.delete(item)
    db.session.commit()
    
    return jsonify(message="Item deleted successfully")

if __name__ == '__main__':
    db.create_all()  # Create database tables
    app.run(debug=False)
