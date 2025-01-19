// Handle Signup Form
document.getElementById('signupForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = {
        email: document.getElementById('signupEmail').value,
        password: document.getElementById('signupPassword').value,
        full_name: document.getElementById('signupFullName').value
    };

    try {
        const response = await fetch('/signup', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });

        const data = await response.json();
        
        if (response.ok) {
            alert('Signup successful!');
            window.location.href = '/login'; // Redirect to login page
        } else {
            alert(`Signup failed: ${data.detail}`);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred during signup');
    }
});

// Handle Login Form
document.getElementById('loginForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = new FormData();
    formData.append('username', document.getElementById('loginEmail').value);
    formData.append('password', document.getElementById('loginPassword').value);

    try {
        const response = await fetch('/token', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        
        if (response.ok) {
            // Store the token in localStorage
            localStorage.setItem('token', data.access_token);
            alert('Login successful!');
            window.location.href = '/protected'; // Redirect to protected page
        } else {
            alert(`Login failed: ${data.detail}`);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred during login');
    }
});

// Check if user is logged in
function checkAuth() {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '/login';
    }
}

// Logout function
function logout() {
    localStorage.removeItem('token');
    window.location.href = '/login';
}