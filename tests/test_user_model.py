import unittest
from app import create_app, db
from app.models import User, Role


class UserModelTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
    
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_password_setter(self):
        u = User(password = 'cat')
        self.assertTrue(u.password_hash is not None)
    
    def test_no_password_getter(self):
        u = User(password = 'cat')
        with self.assertRaises(AttributeError):
            u.password
            
    def test_password_verification(self):
        u = User(password = 'cat')
        self.assertTrue(u.verify_password('cat'))
        self.assertFalse(u.verify_password('dog'))
        
    def test_password_salts_are_random(self):
        u = User(password='cat')
        u2 = User(password='cat')
        self.assertTrue(u.password_hash != u2.password_hash)
        
    def test_valid_confirmation_token(self):
        u = User(password='cat', email='asad', username='dassdada', role_id=3)
        db.session.add(u)
        db.session.commit()
        token = u.generate_confirmation_token()
        self.assertTrue(u.confirm(token))
        
    def test_invalid_confirmation_token(self):
        u1 = User(password='cat', email='asad', username='dassdada', role_id=3)
        u2 = User(password='dog', email='asd', username='dsdada', role_id=3)
        db.session.add(u1)
        db.session.add(u2)
        db.session.commit()
        token = u1.generate_confirmation_token()
        self.assertFalse(u2.confirm(token))
        
    def test_valid_reset_token(self):
        u = User(password='cat', email='asad', username='dassdada', role_id=3)
        db.session.add(u)
        db.session.commit()
        token = u.generate_reset_token()
        self.assertTrue(User.reset_password(token, 'dog'))
        self.assertTrue(u.verify_password('dog'))
        
    def test_invalid_reset_token(self):
        u = User(password='cat', email='asad', username='dassdada', role_id=3)
        db.session.add(u)
        db.session.commit()
        token = u.generate_reset_token()
        self.assertFalse(User.reset_password(token + 'a'.encode('utf-8'), 'horse'))
        self.assertTrue(u.verify_password('cat'))
        
    def test_valid_email_change_token(self):
        u = User(email='jo@example.com', password='cat', username='dassdada', role_id=3)
        db.session.add(u)
        db.session.commit()
        token = u.generate_email_change_token('san@example.org')
        self.assertTrue(u.change_email(token))
        self.assertTrue(u.email == 'san@example.org')
        
    def test_invalid_email_change_token(self):
        u1 = User(email='john@example.com', password='cat', username='dassada', role_id=3)
        u2 = User(email='susan@example.org', password='dog', username='dasada', role_id=3)
        db.session.add(u1)
        db.session.add(u2)
        db.session.commit()
        token = u1.generate_email_change_token('david@example.net')
        self.assertFalse(u2.change_email(token))
        self.assertTrue(u2.email == 'susan@example.org')
        
    def test_duplicate_email_change_token(self):
        u1 = User(email='john@example.com', password='cat', username='dasdada', role_id=3)
        u2 = User(email='susan@example.org', password='dog', username='dada', role_id=3)
        db.session.add(u1)
        db.session.add(u2)
        db.session.commit()
        token = u2.generate_email_change_token('john@example.com')
        self.assertFalse(u2.change_email(token))
        self.assertTrue(u2.email == 'susan@example.org')