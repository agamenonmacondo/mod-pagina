document.addEventListener('DOMContentLoaded', function() {
  // Variables
  const header = document.querySelector('header');
  const menuToggle = document.querySelector('.menu-toggle');
  const nav = document.querySelector('nav');
  const fadeElements = document.querySelectorAll('.fade-in');
  const contactForm = document.querySelector('.contact-form');
  const successMessage = document.querySelector('.success-message');

  // Scroll event for sticky header
  window.addEventListener('scroll', function() {
    if (window.scrollY > 100) {
      header.classList.add('scrolled');
    } else {
      header.classList.remove('scrolled');
    }
    
    // Check for fade-in elements
    fadeElements.forEach(element => {
      const elementPosition = element.getBoundingClientRect().top;
      const screenPosition = window.innerHeight / 1.3;
      
      if (elementPosition < screenPosition) {
        element.classList.add('active');
      }
    });
  });

  // Mobile menu toggle
  if (menuToggle) {
    menuToggle.addEventListener('click', function() {
      menuToggle.classList.toggle('active');
      nav.classList.toggle('active');
      document.body.classList.toggle('menu-open');
    });
  }

  // Close mobile menu when clicking on a link
  const navLinks = document.querySelectorAll('nav ul li a');
  navLinks.forEach(link => {
    link.addEventListener('click', function() {
      if (menuToggle.classList.contains('active')) {
        menuToggle.classList.remove('active');
        nav.classList.remove('active');
        document.body.classList.remove('menu-open');
      }
    });
  });

  // Smooth scrolling for anchor links
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
      e.preventDefault();
      
      const targetId = this.getAttribute('href');
      if (targetId === '#') return;
      
      const targetElement = document.querySelector(targetId);
      if (targetElement) {
        window.scrollTo({
          top: targetElement.offsetTop - 100,
          behavior: 'smooth'
        });
      }
    });
  });

  // Form validation
  if (contactForm) {
    contactForm.addEventListener('submit', function(e) {
      e.preventDefault();
      
      let isValid = true;
      const nameInput = document.getElementById('name');
      const emailInput = document.getElementById('email');
      const messageInput = document.getElementById('message');
      
      // Reset error messages
      document.querySelectorAll('.error-message').forEach(error => {
        error.style.display = 'none';
      });
      
      // Validate name
      if (nameInput.value.trim() === '') {
        document.getElementById('name-error').style.display = 'block';
        isValid = false;
      }
      
      // Validate email
      if (!isValidEmail(emailInput.value)) {
        document.getElementById('email-error').style.display = 'block';
        isValid = false;
      }
      
      // Validate message
      if (messageInput.value.trim() === '') {
        document.getElementById('message-error').style.display = 'block';
        isValid = false;
      }
      
      // If form is valid, show success message
      if (isValid) {
        // En una aplicación real, aquí enviarías los datos al servidor
        contactForm.reset();
        successMessage.classList.add('active');
        
        // Ocultar el mensaje después de 5 segundos
        setTimeout(() => {
          successMessage.classList.remove('active');
        }, 5000);
      }
    });
  }

  // Función para validar email
  function isValidEmail(email) {
    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailPattern.test(email);
  }

  // Initialize fade-in elements
  fadeElements.forEach(element => {
    const elementPosition = element.getBoundingClientRect().top;
    const screenPosition = window.innerHeight / 1.3;
    
    if (elementPosition < screenPosition) {
      element.classList.add('active');
    }
  });
  
  // Iniciar la animación del chat después de 2 segundos
  setTimeout(() => {
    const chatButton = document.getElementById('chat-button');
    if (chatButton) {
      chatButton.classList.add('pulse');
    }
  }, 2000);
}); 