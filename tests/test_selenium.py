import re
import threading
import time
import unittest
from selenium import webdriver
from selenium.webdriver.common.by import By
from app import create_app, db, fake
from app.models import Role, User, Post


class SeleniumTestCase(unittest.TestCase):
    client = None
    HOST = 'localhost'
    PORT = 5000
    
    @classmethod
    def setUpClass(cls) -> None:
        # start Chrome
        options = webdriver.ChromeOptions()
        options.add_argument('-headless')
        try:
            cls.client = webdriver.Chrome(options=options)
        except:
            pass
        
        # skip these tests if the browser could not be started
        if cls.client:
            # create the application
            cls.app = create_app('testing-with-selenium')
            cls.app_context = cls.app.app_context()
            cls.app_context.push()
            
            # suppress logging to keep unittest output clean
            import logging
            logger = logging.getLogger('werkzeug')
            logger.setLevel('ERROR')
            
            # create the database and populate with some fake data
            db.create_all()
            Role.insert_roles()
            fake.users(10)
            fake.posts(10)
            
            # add an administrator user
            admin_role = Role.query.filter_by(name='Administrator').first()
            admin = User(email='h66@e.com',
                         username='she', password='123444',
                         role=admin_role, confirmed=True)
            db.session.add(admin)
            db.session.commit()
            
            # start the Flask server in a thread
            cls.server_thread = threading.Thread(target=cls.app.run,
                                                 kwargs={'host': cls.HOST,
                                                         'port': cls.PORT,
                                                         'debug': False,
                                                         'use_reloader': False},
                                                 daemon=True)
            cls.server_thread.start()
            # give the server a second to ensure it is up

            
    @classmethod
    def tearDownClass(cls) -> None:
        if cls.client:
            # stop the flask server and the browser
            cls.client.get(f'http://{cls.HOST}:{cls.PORT}/shutdown')
            cls.client.quit()
            cls.server_thread.join(2)
            
            # destroy database
            db.drop_all()
            db.session.remove()
            
            # remove application context
            cls.app_context.pop()
            
    def setUp(self) -> None:
        if not self.client:
            self.skipTest('Web browser not available') 
        
    def tearDown(self) -> None:
        pass
    
    def test_admin_home_page(self):
        # navigate to home page
        self.client.get(f'http://{self.HOST}:{self.PORT}/')
        self.assertTrue(re.search('Hello, Stranger!',
                                  self.client.page_source))
        
        # navigate to login page
        self.client.find_element(By.LINK_TEXT, 'Log In').click()
        self.assertIn('<h1>Login</h1>', self.client.page_source)
        
        # login
        self.client.find_element(By.NAME, 'email').send_keys('ne@c.com')
        self.client.find_element(By.NAME, 'password').send_keys('123')
        #self.client.save_screenshot('C:\\Users\\Flask_\\app\\f.png')
        self.client.find_element(By.NAME, 'submit').click()
        self.assertTrue(re.search('Hello, io!', self.client.page_source))
        
        # navigate to the user's profile page
        self.client.find_element(By.LINK_TEXT, 'Profile').click()
        self.assertIn('<h1>io</h1>', self.client.page_source)