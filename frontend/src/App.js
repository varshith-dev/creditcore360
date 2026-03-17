import React, { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import 'bootstrap/dist/css/bootstrap.min.css';
import 'react-toastify/dist/ReactToastify.css';
import './App.css';

// Lazy load components for better performance
const UploadScreen = lazy(() => import('./components/UploadScreen'));
const OfficerPortal = lazy(() => import('./components/OfficerPortal'));
const ProductionReadyDashboard = lazy(() => import('./components/ProductionReadyDashboard'));
const CAMPreview = lazy(() => import('./components/CAMPreview'));
const NotFound = lazy(() => import('./components/NotFound'));

// Loading component
const LoadingSpinner = () => (
  <div className="d-flex justify-content-center align-items-center" style={{ height: '200px' }}>
    <div className="spinner-border text-primary" role="status">
      <span className="visually-hidden">Loading...</span>
    </div>
  </div>
);

function App() {
  return (
    <div className="App">
      <Helmet>
        <title>Intelli-Credit - AI Credit Appraisal</title>
        <meta name="description" content="AI-Powered Corporate Credit Appraisal Engine" />
      </Helmet>
      
      <Router>
        <Suspense fallback={<LoadingSpinner />}>
          <Routes>
            <Route path="/" element={<Navigate to="/upload" replace />} />
            <Route path="/upload" element={<UploadScreen />} />
            <Route path="/portal" element={<OfficerPortal />} />
            <Route path="/results" element={<ProductionReadyDashboard />} />
            <Route path="/preview" element={<CAMPreview />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Suspense>
      </Router>
    </div>
  );
}

export default App;
