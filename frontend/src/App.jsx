import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { AgentProvider } from './context/AgentContext';
import AgentBuilder from './components/AgentBuilder';
import TestAgent from './components/TestAgent';
import './styles/index.css';

/**
 * Root App component
 * Sets up routing and wraps the application with the AgentProvider context
 */
function App() {
  return (
    <Router>
      <AgentProvider>
        <div className="app">
          <header className="app-header">
            <h1>Agent Builder</h1>
            <nav className="app-nav">
              <Link to="/" className="nav-link">Builder</Link>
              <Link to="/test" className="nav-link">Test Agent</Link>
            </nav>
          </header>
          
          <main className="app-content">
            <Routes>
              <Route path="/" element={<AgentBuilder />} />
              <Route path="/test" element={<TestAgent />} />
            </Routes>
          </main>
          
          <footer className="app-footer">
            <p>Powered by LLMs · {new Date().getFullYear()}</p>
          </footer>
        </div>
      </AgentProvider>
    </Router>
  );
}

export default App;