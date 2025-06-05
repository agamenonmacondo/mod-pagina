#!/usr/bin/env python3
"""
Unit Tests for Chat Routes - Image Upload Functionality
======================================================

Tests the analyze_image endpoint to verify that images are correctly
received, processed, and sent to the backend.
"""


# Add project root to path for absolute imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the module to test

# Import Flask testing utilities

class TestChatRoutesImageUpload(unittest.TestCase):
    """Test cases for image upload functionality in chat routes"""
    
    def setUp(self):
        """Set up test environment before each test"""
        self.app = Flask(__name__)
        self.app.register_blueprint(chat_bp)
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        # Create a test image in memory
        self.test_image_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x01\x00\x00\x00\x007n\xf9$\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82'
        
    def create_test_image_file(self, filename='test.png', content_type='image/png'):
        """Helper method to create test image file"""
        return (BytesIO(self.test_image_data), filename), content_type
    
    @patch('routes.chat_routes.ava_process')
    @patch('routes.chat_routes.start_ava')
    @patch('routes.chat_routes.send_to_ava')
    @patch('os.path.exists')
    @patch('pathlib.Path.mkdir')
    def test_analyze_image_success_text_response(self, mock_mkdir, mock_exists, mock_send_ava, mock_start_ava, mock_ava_process):
        """Test successful image upload with text response from AVA"""
        # Setup mocks
        mock_ava_process.poll.return_value = None  # Process is running
        mock_start_ava.return_value = True
        mock_send_ava.return_value = "Esta es una imagen de prueba con contenido interesante."
        mock_exists.return_value = True
        
        # Mock file save
        with patch('builtins.open', mock_open()) as mock_file:
            with patch('uuid.uuid4') as mock_uuid:
                mock_uuid.return_value.hex = 'abcd1234abcd1234'
                
                # Create test data
                data = {
                    'image': self.create_test_image_file()[0],
                    'message': 'Analiza esta imagen de prueba',
                    'unlimited': 'false'
                }
                
                # Make request
                response = self.client.post(
                    '/api/chat/image-analysis',
                    data=data,
                    content_type='multipart/form-data'
                )
                
                # Verify response
                self.assertEqual(response.status_code, 200)
                response_data = json.loads(response.data)
                
                self.assertTrue(response_data['success'])
                self.assertEqual(response_data['response'], "Esta es una imagen de prueba con contenido interesante.")
                self.assertFalse(response_data['image_generated'])
                self.assertIn('user_image_filename', response_data)
                self.assertEqual(response_data['analysis_type'], 'image_upload')
                
                # Verify AVA was called with correct message format
                mock_send_ava.assert_called_once()
                call_args = mock_send_ava.call_args[0][0]
                self.assertIn('Analiza esta imagen de prueba', call_args)
                self.assertIn('[IMAGEN_BASE64:', call_args)
                self.assertIn('[RUTA_IMAGEN:', call_args)
    
    @patch('routes.chat_routes.ava_process')
    @patch('routes.chat_routes.start_ava')
    @patch('routes.chat_routes.send_to_ava_unlimited')
    @patch('os.path.exists')
    @patch('pathlib.Path.mkdir')
    def test_analyze_image_success_with_generated_image(self, mock_mkdir, mock_exists, mock_send_ava_unlimited, mock_start_ava, mock_ava_process):
        """Test successful image upload with AVA generating an image response"""
        # Setup mocks
        mock_ava_process.poll.return_value = None
        mock_start_ava.return_value = True
        mock_send_ava_unlimited.return_value = {
            'text': 'He analizado tu imagen y generé una nueva basada en ella.',
            'image_generated': True,
            'image_filename': 'ava_generated_20241201_143022.png',
            'image_url': '/api/chat/image/ava_generated_20241201_143022.png'
        }
        mock_exists.return_value = True
        
        with patch('builtins.open', mock_open()) as mock_file:
            with patch('uuid.uuid4') as mock_uuid:
                mock_uuid.return_value.hex = 'efgh5678efgh5678'
                
                data = {
                    'image': self.create_test_image_file()[0],
                    'message': 'Genera una nueva imagen basada en esta',
                    'unlimited': 'true'
                }
                
                response = self.client.post(
                    '/api/chat/image-analysis',
                    data=data,
                    content_type='multipart/form-data'
                )
                
                self.assertEqual(response.status_code, 200)
                response_data = json.loads(response.data)
                
                self.assertTrue(response_data['success'])
                self.assertTrue(response_data['image_generated'])
                self.assertEqual(response_data['image_filename'], 'ava_generated_20241201_143022.png')
                self.assertEqual(response_data['image_url'], '/api/chat/image/ava_generated_20241201_143022.png')
                self.assertIn('user_image_filename', response_data)
    
    def test_analyze_image_no_file_uploaded(self):
        """Test error when no image file is uploaded"""
        response = self.client.post(
            '/api/chat/image-analysis',
            data={'message': 'Analiza imagen'},
            content_type='multipart/form-data'
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.data)
        self.assertFalse(response_data['success'])
        self.assertEqual(response_data['response'], 'No se recibió ninguna imagen')
    
    def test_analyze_image_empty_filename(self):
        """Test error when uploaded file has empty filename"""
        data = {
            'image': (BytesIO(self.test_image_data), ''),
            'message': 'Analiza imagen'
        }
        
        response = self.client.post(
            '/api/chat/image-analysis',
            data=data,
            content_type='multipart/form-data'
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.data)
        self.assertFalse(response_data['success'])
        self.assertEqual(response_data['response'], 'Archivo vacío')
    
    def test_analyze_image_invalid_file_type(self):
        """Test error when uploaded file is not an image"""
        data = {
            'image': (BytesIO(b'not an image'), 'test.txt'),
            'message': 'Analiza imagen'
        }
        
        # Mock the content_type to simulate a text file
        with patch('werkzeug.datastructures.FileStorage.content_type', 'text/plain'):
            response = self.client.post(
                '/api/chat/image-analysis',
                data=data,
                content_type='multipart/form-data'
            )
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.data)
        self.assertFalse(response_data['success'])
        self.assertEqual(response_data['response'], 'El archivo debe ser una imagen')
    
    @patch('routes.chat_routes.ava_process')
    @patch('routes.chat_routes.start_ava')
    def test_analyze_image_ava_start_failure(self, mock_start_ava, mock_ava_process):
        """Test error when AVA fails to start"""
        mock_ava_process.poll.return_value = 1  # Process not running
        mock_start_ava.return_value = False  # Failed to start
        
        with patch('os.path.exists', return_value=True):
            with patch('pathlib.Path.mkdir'):
                with patch('builtins.open', mock_open()):
                    data = {
                        'image': self.create_test_image_file()[0],
                        'message': 'Analiza imagen'
                    }
                    
                    response = self.client.post(
                        '/api/chat/image-analysis',
                        data=data,
                        content_type='multipart/form-data'
                    )
                    
                    self.assertEqual(response.status_code, 500)
                    response_data = json.loads(response.data)
                    self.assertFalse(response_data['success'])
                    self.assertEqual(response_data['response'], 'Error iniciando AVA para análisis')
    
    @patch('routes.chat_routes.ava_process')
    @patch('routes.chat_routes.start_ava')
    @patch('routes.chat_routes.send_to_ava')
    @patch('os.path.exists')
    @patch('pathlib.Path.mkdir')
    def test_analyze_image_base64_encoding(self, mock_mkdir, mock_exists, mock_send_ava, mock_start_ava, mock_ava_process):
        """Test that image is correctly converted to Base64"""
        mock_ava_process.poll.return_value = None
        mock_start_ava.return_value = True
        mock_send_ava.return_value = "Imagen analizada correctamente"
        mock_exists.return_value = True
        
        test_image_b64 = base64.b64encode(self.test_image_data).decode('utf-8')
        
        with patch('builtins.open', mock_open(read_data=self.test_image_data)) as mock_file:
            with patch('uuid.uuid4') as mock_uuid:
                mock_uuid.return_value.hex = 'test1234test1234'
                
                data = {
                    'image': self.create_test_image_file()[0],
                    'message': 'Analiza imagen'
                }
                
                response = self.client.post(
                    '/api/chat/image-analysis',
                    data=data,
                    content_type='multipart/form-data'
                )
                
                # Verify Base64 encoding in message sent to AVA
                mock_send_ava.assert_called_once()
                ava_message = mock_send_ava.call_args[0][0]
                self.assertIn(f'data:image/png;base64,{test_image_b64}', ava_message)
    
    @patch('routes.chat_routes.ava_process')
    @patch('routes.chat_routes.start_ava')
    @patch('routes.chat_routes.send_to_ava')
    @patch('os.path.exists')
    @patch('pathlib.Path.mkdir')
    def test_analyze_image_different_formats(self, mock_mkdir, mock_exists, mock_send_ava, mock_start_ava, mock_ava_process):
        """Test handling of different image formats (JPG, PNG)"""
        mock_ava_process.poll.return_value = None
        mock_start_ava.return_value = True
        mock_send_ava.return_value = "Formato procesado correctamente"
        mock_exists.return_value = True
        
        # Test JPG format
        with patch('builtins.open', mock_open(read_data=self.test_image_data)):
            with patch('uuid.uuid4') as mock_uuid:
                mock_uuid.return_value.hex = 'jpg123jpg123'
                
                data = {
                    'image': (BytesIO(self.test_image_data), 'test.jpg'),
                    'message': 'Analiza JPG'
                }
                
                response = self.client.post(
                    '/api/chat/image-analysis',
                    data=data,
                    content_type='multipart/form-data'
                )
                
                self.assertEqual(response.status_code, 200)
                response_data = json.loads(response.data)
                self.assertTrue(response_data['success'])
                
                # Verify JPG extension in filename
                ava_message = mock_send_ava.call_args[0][0]
                self.assertIn('data:image/jpg;base64,', ava_message)
    
    def test_analyze_image_exception_handling(self):
        """Test exception handling in analyze_image endpoint"""
        # Force an exception by mocking a critical function
        with patch('routes.chat_routes.logger') as mock_logger:
            with patch('uuid.uuid4', side_effect=Exception("Test exception")):
                data = {
                    'image': self.create_test_image_file()[0],
                    'message': 'Test exception'
                }
                
                response = self.client.post(
                    '/api/chat/image-analysis',
                    data=data,
                    content_type='multipart/form-data'
                )
                
                self.assertEqual(response.status_code, 500)
                response_data = json.loads(response.data)
                self.assertFalse(response_data['success'])
                self.assertIn('Error procesando imagen', response_data['response'])
                
                # Verify error was logged
                mock_logger.error.assert_called()


class TestIntegrationImageUpload(unittest.TestCase):
    """Integration tests for complete image upload workflow"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.app = Flask(__name__)
        self.app.register_blueprint(chat_bp)
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
    
    @patch('routes.chat_routes.ava_process')
    @patch('routes.chat_routes.start_ava')
    @patch('routes.chat_routes.send_to_ava')
    @patch('os.path.exists')
    @patch('pathlib.Path.mkdir') 
    @patch('pathlib.Path.exists')
    def test_complete_image_workflow(self, mock_path_exists, mock_mkdir, mock_exists, mock_send_ava, mock_start_ava, mock_ava_process):
        """Test complete workflow from image upload to AVA response"""
        # Setup mocks for successful workflow
        mock_ava_process.poll.return_value = None
        mock_start_ava.return_value = True
        mock_send_ava.return_value = "Imagen procesada: Veo una imagen de prueba PNG de 1x1 pixel."
        mock_exists.return_value = True
        mock_path_exists.return_value = True
        
        test_image = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x01\x00\x00\x00\x007n\xf9$\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82'
        
        with patch('builtins.open', mock_open(read_data=test_image)) as mock_file:
            with patch('uuid.uuid4') as mock_uuid:
                mock_uuid.return_value.hex = 'integration123'
                
                # Test data
                data = {
                    'image': (BytesIO(test_image), 'integration_test.png'),
                    'message': 'Describe qué ves en esta imagen',
                    'unlimited': 'false'
                }
                
                # Make request
                response = self.client.post(
                    '/api/chat/image-analysis',
                    data=data,
                    content_type='multipart/form-data'
                )
                
                # Verify complete workflow
                self.assertEqual(response.status_code, 200)
                response_data = json.loads(response.data)
                
                # Verify response structure
                expected_keys = [
                    'success', 'response', 'image_generated', 
                    'user_image_path', 'user_image_filename', 
                    'timestamp', 'analysis_type'
                ]
                for key in expected_keys:
                    self.assertIn(key, response_data)
                
                # Verify response content
                self.assertTrue(response_data['success'])
                self.assertIn('Imagen procesada', response_data['response'])
                self.assertEqual(response_data['analysis_type'], 'image_upload')
                self.assertIn('user_upload_integrati', response_data['user_image_filename'])
                
                # Verify AVA was called with properly formatted message
                mock_send_ava.assert_called_once()
                ava_message = mock_send_ava.call_args[0][0]
                
                # Verify message contains all required components
                self.assertIn('Describe qué ves en esta imagen', ava_message)
                self.assertIn('[IMAGEN_BASE64: data:image/png;base64,', ava_message)
                self.assertIn('[RUTA_IMAGEN:', ava_message)
                # Since 'routes' is a namespace package, use an absolute import

class TestChatRoutesImageAnalysis(unittest.TestCase):

    def setUp(self):
        """Set up a test Flask app and test client."""
        self.app = Flask(__name__)
        self.app.register_blueprint(chat_bp)
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

        # Define the path for uploaded images, consistent with chat_routes.py
        # Assuming test_chat_routes.py is in 'routes' directory, and chat_routes.py is also in 'routes'
        # Path(__file__).parent is 'routes'
        # Path(__file__).parent.parent is the project root
        self.project_root = Path(__file__).parent.parent
        self.uploaded_images_dir = self.project_root / 'llmpagina' / 'ava_bot' / 'uploaded images'
        
        # Create the directory if it doesn't exist
        self.uploaded_images_dir.mkdir(parents=True, exist_ok=True)

        # Mock external dependencies
        self.patch_start_ava = patch('routes.chat_routes.start_ava')
        self.mock_start_ava = self.patch_start_ava.start()
        self.mock_start_ava.return_value = True # Assume AVA starts successfully by default

        self.patch_send_to_ava = patch('routes.chat_routes.send_to_ava')
        self.mock_send_to_ava = self.patch_send_to_ava.start()

        self.patch_send_to_ava_unlimited = patch('routes.chat_routes.send_to_ava_unlimited')
        self.mock_send_to_ava_unlimited = self.patch_send_to_ava_unlimited.start()
        
        # Reset global ava_process state for relevant tests
        global global_ava_process
        global_ava_process = None


    def tearDown(self):
        """Clean up after tests."""
        self.patch_start_ava.stop()
        self.patch_send_to_ava.stop()
        self.patch_send_to_ava_unlimited.stop()

        # Remove the uploaded images directory and its contents
        if self.uploaded_images_dir.exists():
            shutil.rmtree(self.uploaded_images_dir)
        
        global global_ava_process
        global_ava_process = None

    def _create_dummy_image(self, filename="test_image.png", content_type="image/png"):
        """Creates a dummy image file for uploads."""
        return (BytesIO(b"dummyimagecontent"), filename, content_type)

    def test_analyze_image_success_text_response(self):
        """Test successful image analysis with a text response from AVA."""
        self.mock_send_to_ava.return_value = "Image analyzed successfully."
        
        # Ensure ava_process is None so start_ava is called
        global global_ava_process
        global_ava_process = None

        data = {
            'message': 'Analyze this test image',
            'unlimited': 'false',
            'image': self._create_dummy_image()
        }
        response = self.client.post('/api/chat/image-analysis', data=data, content_type='multipart/form-data')
        
        self.assertEqual(response.status_code, 200)
        json_response = response.get_json()
        
        self.assertTrue(json_response['success'])
        self.assertEqual(json_response['response'], "Image analyzed successfully.")
        self.assertFalse(json_response['image_generated'])
        self.assertIn('user_image_filename', json_response)
        self.assertTrue(json_response['user_image_filename'].startswith('user_upload_'))
        self.assertTrue(json_response['user_image_filename'].endswith('.png'))
        self.assertEqual(json_response['analysis_type'], 'image_upload')

        # Verify the image was saved
        saved_image_path = self.uploaded_images_dir / json_response['user_image_filename']
        self.assertTrue(saved_image_path.exists())
        self.mock_start_ava.assert_called_once()
        self.mock_send_to_ava.assert_called_once()

    def test_analyze_image_success_ava_generates_image(self):
        """Test successful analysis where AVA also generates an image."""
        ava_response = {
            'text': 'Analyzed and generated a new image.',
            'image_generated': True,
            'image_url': '/api/chat/image/ava_generated.png',
            'image_filename': 'ava_generated.png'
        }