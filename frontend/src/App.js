import React, { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import 'bootstrap/dist/css/bootstrap.min.css';
import 'react-toastify/dist/ReactToastify.css';
import './App.css';

// Layout
import Layout from './components/Layout';

// Lazy load components for better performance
const UploadScreen = lazy(() => import('./components/UploadScreen'));
const OfficerPortal = lazy(() => import('./components/OfficerPortal'));
const ProductionReadyDashboard = lazy(() => import('./components/ProductionReadyDashboard'));
const CAMPreview = lazy(() => import('./components/CAMPreview'));
const NotFound = lazy(() => import('./components/NotFound'));

// Loading component
const LoadingSpinner = () => (
  <div className="d-flex justify-content-center align-items-center min-vh-100">
    <div className="spinner-border text-primary" role="status" style={{ width: '3rem', height: '3rem' }}>
      <span className="visually-hidden">Loading Module...</span>
    </div>
  </div>
);

function App() {
  return (
    <div className="App bg-light min-vh-100">
      <Helmet>
        <title>Intelli-Credit - AI Credit Appraisal</title>
        <meta name="description" content="AI-Powered Corporate Credit Appraisal Engine - Frontend" />
      </Helmet>
      
      <Router>
        <Suspense fallback={<LoadingSpinner />}>
          <Routes>
            <Route path="/" element={<Navigate to="/upload" replace />} />
            
            {/* Wrap application routes in Layout */}
            <Route path="/upload" element={<Layout><UploadScreen /></Layout>} />
            <Route path="/portal" element={<Layout><OfficerPortal /></Layout>} />
            <Route path="/results" element={<Layout><ProductionReadyDashboard /></Layout>} />
            <Route path="/preview" element={<Layout><CAMPreview /></Layout>} />
            
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Suspense>
      </Router>
    </div>
  );
}

export default App;
