# RAG Application Frontend

A Next.js frontend for the RAG (Retrieval-Augmented Generation) application with Firebase authentication.

## Setup

### Prerequisites

- Node.js 18+ and npm/yarn
- Firebase project with Authentication enabled

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   npm install
   # or
   yarn install
   ```

3. Install Firebase:
   ```bash
   npm install firebase
   # or
   yarn add firebase
   ```

4. Set up environment variables:
   - Copy `.env.local.example` to `.env.local`
   - Fill in your Firebase project details

### Firebase Configuration

1. Create a Firebase project at [https://console.firebase.google.com/](https://console.firebase.google.com/)
2. Enable Email/Password authentication in the Firebase console
3. Get your Firebase configuration from Project Settings > General > Your apps > Web app
4. Add the configuration to your `.env.local` file

## Authentication

The application uses Firebase Authentication with the following features:

- Email/Password authentication
- Protected routes
- Authentication state management with React Context

### Using Authentication in Components

```tsx
import { useAuth } from '../context/AuthContext';

const MyComponent = () => {
  const { user, loading, error, logIn, logOut } = useAuth();

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div>
      {user ? (
        <div>
          <p>Welcome, {user.email}</p>
          <button onClick={logOut}>Log Out</button>
        </div>
      ) : (
        <button onClick={() => logIn('user@example.com', 'password')}>
          Log In
        </button>
      )}
    </div>
  );
};
```

### Making Authenticated API Requests

```tsx
import { useAuth } from '../context/AuthContext';

const MyComponent = () => {
  const { getIdToken } = useAuth();

  const fetchData = async () => {
    const token = await getIdToken();
    if (!token) return;

    const response = await fetch('/api/protected-route', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    const data = await response.json();
    // Handle data
  };

  return <button onClick={fetchData}>Fetch Data</button>;
};
```

## Development

Run the development server:

```bash
npm run dev
# or
yarn dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser to see the application.

## Production

Build the application for production:

```bash
npm run build
# or
yarn build
```

Start the production server:

```bash
npm start
# or
yarn start
``` 