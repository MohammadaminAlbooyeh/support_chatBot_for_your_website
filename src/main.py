from flask import Flask, render_template_string, request, jsonify, session
try:
    from flask_sqlalchemy import SQLAlchemy
except Exception:
    SQLAlchemy = None

from werkzeug.utils import secure_filename
from datetime import datetime
import uuid
import os
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chatbot.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

db = SQLAlchemy(app) if SQLAlchemy is not None else None

# Database Models
if db is not None:
    class Conversation(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        session_id = db.Column(db.String(100), nullable=False)
        message = db.Column(db.Text, nullable=False)
        response = db.Column(db.Text, nullable=False)
        timestamp = db.Column(db.DateTime, default=datetime.utcnow)
        user_type = db.Column(db.String(20), default='user')  # 'user' or 'agent'

    class SupportTicket(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        session_id = db.Column(db.String(100), nullable=False)
        status = db.Column(db.String(20), default='open')  # 'open', 'assigned', 'closed'
        priority = db.Column(db.String(10), default='medium')  # 'low', 'medium', 'high'
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        assigned_agent = db.Column(db.String(100))

    class UploadedFile(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        session_id = db.Column(db.String(100), nullable=False)
        filename = db.Column(db.String(200), nullable=False)
        original_filename = db.Column(db.String(200), nullable=False)
        upload_time = db.Column(db.DateTime, default=datetime.utcnow)
else:
    # Lightweight fallbacks so module can be imported without SQLAlchemy
    class Conversation:
        def __init__(self, *args, **kwargs):
            pass

    class SupportTicket:
        def __init__(self, *args, **kwargs):
            pass

    class UploadedFile:
        def __init__(self, *args, **kwargs):
            pass

# Enhanced response system with categories
responses = {
    # Greetings
    "hello": "Hi there! Welcome to our support center. How can I assist you today?",
    "hi": "Hello! I'm here to help with any questions you have.",
    
    # Billing Support
    "billing": "I can help with billing questions. Are you looking for invoice details, payment issues, or subscription changes?",
    "payment": "For payment issues, I can help you with: \n• Payment methods\n• Failed payments\n• Refund requests\n• Billing address updates",
    "refund": "I understand you'd like a refund. Let me connect you with our billing specialist who can review your account.",
    "invoice": "You can find your invoices in your account dashboard. Would you like me to guide you there?",
    
    # Technical Support
    "technical": "I'm here for technical support! What specific issue are you experiencing?",
    "bug": "Sorry to hear about the technical issue. Can you describe what happened? Feel free to upload screenshots if helpful.",
    "error": "Let's troubleshoot this error together. What error message are you seeing?",
    "login": "Having trouble logging in? Try: \n• Reset your password\n• Clear browser cache\n• Check your email for verification\n• Contact us if issues persist",
    
    # Account Help
    "account": "I can help with account-related questions including profile updates, security settings, and access issues.",
    "password": "To reset your password, click 'Forgot Password' on the login page. Check your email for reset instructions.",
    "profile": "You can update your profile information in Account Settings. Need help finding it?",
    
    # General Support
    "help": "I'm here to help! I can assist with:\n• Billing and payments\n• Technical issues\n• Account management\n• General questions\n\nWhat would you like help with?",
    "human": "I'll connect you with a human agent right away. Please hold on.",
    "agent": "Transferring you to our live support team. An agent will be with you shortly.",
    
    # Farewells
    "bye": "Thank you for contacting support! Have a great day and don't hesitate to reach out if you need more help.",
    "thanks": "You're welcome! Is there anything else I can help you with today?",
    
    # File upload responses
    "upload": "Great! I can see you've uploaded a file. This will help our team assist you better.",
    
    # Default
    "default": "I'm not sure I understand. Could you please rephrase that? Or type 'help' to see what I can assist with."
}

# FAQ responses
faq_responses = {
    "how to cancel": "To cancel your subscription, go to Account Settings > Billing > Cancel Subscription. You'll retain access until your current period ends.",
    "supported browsers": "We support Chrome, Firefox, Safari, and Edge (latest versions). Internet Explorer is not supported.",
    "data security": "Your data is encrypted and stored securely. We're SOC 2 compliant and follow industry best practices for data protection.",
    "contact hours": "Our support team is available Monday-Friday 9AM-6PM EST. Premium users have 24/7 access."
}

def create_tables():
    with app.app_context():
        if db is not None:
            db.create_all()
        # Create upload directory
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def get_session_id():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return session['session_id']

def save_conversation(message, response, session_id, user_type='user'):
    if db is None:
        return
    conversation = Conversation(
        session_id=session_id,
        message=message,
        response=response,
        user_type=user_type
    )
    db.session.add(conversation)
    db.session.commit()

def get_response(message, session_id):
    message_lower = message.lower()
    
    # Check for live agent requests
    if any(word in message_lower for word in ['human', 'agent', 'live chat', 'speak to someone']):
        create_support_ticket(session_id, 'high')
        return "I'm connecting you with a live agent now. Please hold on while I transfer your chat."
    
    # Check FAQ first
    for faq_key, faq_response in faq_responses.items():
        if faq_key in message_lower:
            return faq_response
    
    # Check regular responses
    for key, response in responses.items():
        if key in message_lower:
            return response
    
    # If no match found, suggest alternatives
    return responses["default"] + "\n\nPopular topics: billing, technical support, account help, or type 'human' for live chat."

def create_support_ticket(session_id, priority='medium'):
    if db is None:
        return None
    ticket = SupportTicket(
        session_id=session_id,
        priority=priority
    )
    db.session.add(ticket)
    db.session.commit()
    return ticket.id

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    session_id = get_session_id()
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>Support Center - Live Chat</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0; padding: 20px; background: #f5f5f5;
        }
        .chat-container {
            max-width: 600px; margin: 0 auto; background: white;
            border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .chat-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; padding: 20px; text-align: center;
        }
        .status-indicator {
            display: inline-block; width: 10px; height: 10px;
            background: #4CAF50; border-radius: 50%; margin-right: 8px;
        }
        #chat {
            height: 400px; overflow-y: auto; padding: 20px;
            background: white;
        }
        .message {
            margin: 10px 0; padding: 10px 15px;
            border-radius: 18px; max-width: 80%;
            word-wrap: break-word;
        }
        .user-message {
            background: #007AFF; color: white;
            margin-left: auto; text-align: right;
        }
        .bot-message {
            background: #f1f1f1; color: #333;
            border: 1px solid #e1e1e1;
        }
        .input-container {
            padding: 20px; background: #fafafa;
            border-top: 1px solid #e1e1e1;
        }
        .input-row {
            display: flex; gap: 10px; align-items: center;
        }
        #message {
            flex: 1; padding: 12px 16px; border: 2px solid #e1e1e1;
            border-radius: 25px; outline: none; font-size: 14px;
        }
        #message:focus { border-color: #007AFF; }
        button {
            padding: 12px 20px; background: #007AFF; color: white;
            border: none; border-radius: 20px; cursor: pointer;
            font-weight: 600; transition: all 0.3s;
        }
        button:hover { background: #0056CC; transform: translateY(-1px); }
        .file-upload {
            display: flex; align-items: center; gap: 10px;
            margin-top: 10px;
        }
        .file-input {
            display: none;
        }
        .file-button {
            background: #34C759; padding: 8px 16px;
            font-size: 12px;
        }
        .quick-actions {
            display: flex; gap: 8px; margin-top: 10px;
            flex-wrap: wrap;
        }
        .quick-btn {
            background: #f0f0f0; color: #333;
            border: 1px solid #ddd; padding: 6px 12px;
            font-size: 12px; border-radius: 15px;
        }
        .quick-btn:hover { background: #e0e0e0; }
        .typing-indicator {
            display: none; padding: 10px; font-style: italic;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-header">
            <h1><span class="status-indicator"></span>Support Center</h1>
            <p>We're here to help! Average response time: 2 minutes</p>
        </div>
        
        <div id="chat">
            <div class="message bot-message">
                Welcome! I'm your support assistant. I can help with billing, technical issues, account questions, and more. How can I assist you today?
            </div>
        </div>
        
        <div class="typing-indicator" id="typing">Support is typing...</div>
        
        <div class="input-container">
            <div class="input-row">
                <input type="text" id="message" placeholder="Type your message..." onkeypress="handleKeyPress(event)">
                <button onclick="sendMessage()">Send</button>
            </div>
            
            <div class="file-upload">
                <input type="file" id="fileInput" class="file-input" onchange="uploadFile()" accept=".txt,.pdf,.png,.jpg,.jpeg,.gif,.doc,.docx">
                <button class="file-button" onclick="document.getElementById('fileInput').click()">📎 Upload File</button>
                <span id="fileStatus"></span>
            </div>
            
            <div class="quick-actions">
                <button class="quick-btn" onclick="quickMessage('billing help')">💳 Billing</button>
                <button class="quick-btn" onclick="quickMessage('technical support')">🔧 Technical</button>
                <button class="quick-btn" onclick="quickMessage('account help')">👤 Account</button>
                <button class="quick-btn" onclick="quickMessage('human agent')">💬 Live Chat</button>
            </div>
        </div>
    </div>

    <script>
        let isUploading = false;
        
        function handleKeyPress(event) {
            if (event.key === 'Enter') {
                sendMessage();
            }
        }
        
        function quickMessage(message) {
            document.getElementById('message').value = message;
            sendMessage();
        }
        
        function sendMessage() {
            const messageInput = document.getElementById('message');
            const message = messageInput.value.trim();
            if (message === '' || isUploading) return;

            addMessage(message, 'user');
            messageInput.value = '';
            showTyping();

            fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: message })
            })
            .then(response => response.json())
            .then(data => {
                hideTyping();
                addMessage(data.response, 'bot');
                if (data.ticket_created) {
                    addMessage('✅ Support ticket #' + data.ticket_id + ' created. An agent will join this chat shortly.', 'system');
                }
            })
            .catch(error => {
                hideTyping();
                addMessage('Sorry, there was an error. Please try again.', 'bot');
            });
        }
        
        function uploadFile() {
            const fileInput = document.getElementById('fileInput');
            const file = fileInput.files[0];
            if (!file) return;
            
            isUploading = true;
            const fileStatus = document.getElementById('fileStatus');
            fileStatus.textContent = 'Uploading...';
            
            const formData = new FormData();
            formData.append('file', file);
            
            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                isUploading = false;
                if (data.success) {
                    fileStatus.textContent = '✅ ' + file.name + ' uploaded';
                    addMessage('📎 Uploaded: ' + file.name, 'user');
                    addMessage(data.message, 'bot');
                } else {
                    fileStatus.textContent = '❌ Upload failed';
                    addMessage('Sorry, file upload failed. ' + data.error, 'bot');
                }
                fileInput.value = '';
            })
            .catch(error => {
                isUploading = false;
                fileStatus.textContent = '❌ Upload error';
                addMessage('File upload error. Please try again.', 'bot');
                fileInput.value = '';
            });
        }
        
        function showTyping() {
            document.getElementById('typing').style.display = 'block';
        }
        
        function hideTyping() {
            document.getElementById('typing').style.display = 'none';
        }

        function addMessage(message, type) {
            const chat = document.getElementById('chat');
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message ' + (type === 'user' ? 'user-message' : 'bot-message');
            
            // Convert newlines to HTML breaks
            const formattedMessage = message.replace(/\n/g, '<br>');
            messageDiv.innerHTML = formattedMessage;
            
            chat.appendChild(messageDiv);
            chat.scrollTop = chat.scrollHeight;
        }
        
        // Auto-focus message input
        document.getElementById('message').focus();
    </script>
</body>
</html>
    ''')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    message = data.get('message', '')
    session_id = get_session_id()
    
    response = get_response(message, session_id)
    
    # Save conversation to database
    save_conversation(message, response, session_id)
    
    # Check if a support ticket was created
    ticket_created = 'connecting you with a live agent' in response.lower()
    
    response_data = {'response': response}
    if ticket_created:
        ticket_id = create_support_ticket(session_id, 'high')
        response_data['ticket_created'] = True
        response_data['ticket_id'] = ticket_id
    
    return jsonify(response_data)

@app.route('/upload', methods=['POST'])
def upload_file():
    session_id = get_session_id()
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file selected'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'})
    
    if file and allowed_file(file.filename):
        # Generate secure filename
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        try:
            file.save(filepath)
            
            # Save file info to database (if available)
            if db is not None:
                uploaded_file = UploadedFile(
                    session_id=session_id,
                    filename=unique_filename,
                    original_filename=filename
                )
                db.session.add(uploaded_file)
                db.session.commit()
            
            return jsonify({
                'success': True, 
                'message': f"Thanks for uploading {filename}! I've received your file and our support team can now review it to better assist you."
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': 'File upload failed'})
    
    return jsonify({'success': False, 'error': 'File type not allowed'})

@app.route('/admin/conversations')
def admin_conversations():
    if db is None:
        return jsonify([])
    conversations = Conversation.query.order_by(Conversation.timestamp.desc()).limit(100).all()
    return jsonify([{
        'id': c.id,
        'session_id': c.session_id,
        'message': c.message,
        'response': c.response,
        'timestamp': c.timestamp.isoformat(),
        'user_type': c.user_type
    } for c in conversations])

@app.route('/admin/tickets')
def admin_tickets():
    if db is None:
        return jsonify([])
    tickets = SupportTicket.query.order_by(SupportTicket.created_at.desc()).all()
    return jsonify([{
        'id': t.id,
        'session_id': t.session_id,
        'status': t.status,
        'priority': t.priority,
        'created_at': t.created_at.isoformat(),
        'assigned_agent': t.assigned_agent
    } for t in tickets])

if __name__ == '__main__':
    create_tables()
    app.run(debug=True)