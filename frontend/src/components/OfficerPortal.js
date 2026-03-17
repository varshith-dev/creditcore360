import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import axios from 'axios';
import {
  FaUserEdit,
  FaSave,
  FaExclamationTriangle,
  FaCheckCircle,
  FaTimes,
  FaChartLine,
  FaBrain,
  FaShieldAlt,
  FaSearch
} from 'react-icons/fa';

const OfficerPortal = () => {
  const navigate = useNavigate();
  
  const [observations, setObservations] = useState('');
  const [currentScores, setCurrentScores] = useState({
    character: 75,
    capacity: 80,
    capital: 70,
    collaterall: 65,
    conditions: 72
  });
  const [adjustedScores, setAdjustedScores] = useState(null);
  const [loading, setLoading] = useState(false);
  const [keywords, setKeywords] = useState([]);
  const [analysis, setAnalysis] = useState(null);

  const riskKeywords = [
    { category: 'character', keywords: ['default', 'delay', 'missing', 'late', 'poor', 'weak', 'negative'], impact: -5 },
    { category: 'capacity', keywords: ['declining', 'negative', 'loss', 'cash flow', 'liquidity', 'insufficient'], impact: -8 },
    { category: 'capital', keywords: ['undercapitalized', 'insufficient', 'negative', 'declining', 'risk'], impact: -6 },
    { category: 'collateral', keywords: ['insufficient', 'weak', 'risky', 'inadequate', 'questionable'], impact: -4 },
    { category: 'conditions', keywords: ['volatile', 'uncertain', 'risky', 'challenging', 'difficult'], impact: -3 }
  ];

  const detectKeywords = (text) => {
    const detected = [];
    const lowerText = text.toLowerCase();
    
    riskKeywords.forEach(risk => {
      risk.keywords.forEach(keyword => {
        if (lowerText.includes(keyword)) {
          detected.push({
            keyword,
            category: risk.category,
            impact: risk.impact,
            found: lowerText.match(new RegExp(keyword, 'gi'))?.[0] || keyword
          });
        }
      });
    });
    
    return detected;
  };

  const handleObservationChange = (e) => {
    const text = e.target.value;
    setObservations(text);
    
    const detected = detectKeywords(text);
    setKeywords(detected);
  };

  const processObservations = async () => {
    if (!observations.trim()) {
      toast.error('Please enter observations');
      return;
    }

    setLoading(true);
    
    try {
      const response = await axios.post('/api/research/officer-observations', {
        observations: observations,
        current_scores: currentScores
      });

      if (response.data.classification_result) {
        setAdjustedScores(response.data.classification_result.adjusted_scores);
        setAnalysis(response.data.classification_result);
        toast.success('Observations processed successfully');
      }
    } catch (error) {
      console.error('Error processing observations:', error);
      toast.error('Failed to process observations');
    } finally {
      setLoading(false);
    }
  };

  const saveAdjustments = async () => {
    if (!adjustedScores) {
      toast.error('No adjustments to save');
      return;
    }

    setLoading(true);
    
    try {
      const response = await axios.post('/api/scoring/adjust-scores', {
        adjusted_scores: adjustedScores,
        officer_notes: observations
      });

      toast.success('Score adjustments saved');
      navigate('/results');
    } catch (error) {
      console.error('Error saving adjustments:', error);
      toast.error('Failed to save adjustments');
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 80) return 'success';
    if (score >= 60) return 'warning';
    return 'danger';
  };

  const getScoreIcon = (score) => {
    if (score >= 80) return <FaCheckCircle className="text-success" />;
    if (score >= 60) return <FaExclamationTriangle className="text-warning" />;
    return <FaTimes className="text-danger" />;
  };

  return (
    <div className="officer-portal container-fluid py-4">
      <div className="row justify-content-center">
        <div className="col-lg-10">
          <div className="card shadow-sm">
            <div className="card-header bg-primary text-white">
              <h4 className="mb-0">
                <FaUserEdit className="me-2" />
                Officer Portal - Risk Assessment
              </h4>
            </div>
            <div className="card-body">
              <div className="row">
                {/* Observations Input */}
                <div className="col-md-6 mb-4">
                  <div className="card h-100">
                    <div className="card-header">
                      <h6 className="mb-0">
                        <FaSearch className="me-2" />
                        Field Observations
                      </h6>
                    </div>
                    <div className="card-body">
                      <div className="mb-3">
                        <label htmlFor="observations" className="form-label fw-semibold">
                          Enter your observations about this case:
                        </label>
                        <textarea
                          id="observations"
                          className="form-control"
                          rows="6"
                          value={observations}
                          onChange={handleObservationChange}
                          placeholder="Enter observations about character, capacity, capital, collateral, conditions..."
                        />
                      </div>
                      
                      {/* Detected Keywords */}
                      {keywords.length > 0 && (
                        <div className="detected-keywords">
                          <h6 className="text-warning mb-2">
                            <FaExclamationTriangle className="me-2" />
                            Risk Keywords Detected
                          </h6>
                          <div className="keyword-list">
                            {keywords.map((keyword, index) => (
                              <span
                                key={index}
                                className={`badge bg-${keyword.category === 'character' ? 'danger' : keyword.category === 'capacity' ? 'warning' : 'secondary'} me-1 mb-1`}
                              >
                                {keyword.found} ({keyword.category}: {keyword.impact})
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      <div className="d-flex gap-2 mt-3">
                        <button
                          className="btn btn-primary flex-fill"
                          onClick={processObservations}
                          disabled={loading || !observations.trim()}
                        >
                          {loading ? (
                            <>
                              <div className="spinner-border spinner-border-sm me-2" role="status"></div>
                              Processing...
                            </>
                          ) : (
                            <>
                              <FaBrain className="me-2" />
                              Analyze with AI
                            </>
                          )}
                        </button>
                        
                        <button
                          className="btn btn-outline-secondary flex-fill"
                          onClick={() => setObservations('')}
                          disabled={loading}
                        >
                          <FaTimes />
                          Clear
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Current Scores */}
                <div className="col-md-6 mb-4">
                  <div className="card h-100">
                    <div className="card-header">
                      <h6 className="mb-0">
                        <FaChartLine className="me-2" />
                        Current Five Cs Scores
                      </h6>
                    </div>
                    <div className="card-body">
                      <div className="score-grid">
                        {Object.entries(currentScores).map(([key, value]) => (
                          <div key={key} className="score-item">
                            <div className="d-flex justify-content-between align-items-center">
                              <span className="fw-semibold text-capitalize">{key}</span>
                              <div className="d-flex align-items-center">
                                {getScoreIcon(value)}
                                <span className={`ms-2 fw-bold ${getScoreColor(value)}`}>
                                  {value}/100
                                </span>
                              </div>
                            </div>
                            <input
                              type="range"
                              className="form-range"
                              min="0"
                              max="100"
                              value={value}
                              onChange={(e) => setCurrentScores(prev => ({
                                ...prev,
                                [key]: parseInt(e.target.value)
                              }))}
                            />
                          </div>
                        ))}
                      </div>
                      
                      <div className="mt-3">
                        <small className="text-muted">
                          Adjust scores based on your field observations. The system will automatically detect risk factors and suggest adjustments.
                        </small>
                      </div>
                    </div>
                  </div>
                </div>

                {/* AI Analysis Results */}
                {analysis && (
                  <div className="col-12 mb-4">
                    <div className="card">
                      <div className="card-header bg-info text-white">
                        <h6 className="mb-0">
                          <FaBrain className="me-2" />
                          AI Analysis Results
                        </h6>
                      </div>
                      <div className="card-body">
                        <div className="row">
                          <div className="col-md-6">
                            <h6>Detected Risk Factors:</h6>
                            <ul className="risk-factors">
                              {analysis.detected_keywords?.map((factor, index) => (
                                <li key={index} className="mb-2">
                                  <span className={`badge bg-${factor.severity} me-2`}>
                                    {factor.category}
                                  </span>
                                  {factor.description}
                                </li>
                              ))}
                            </ul>
                          </div>
                          
                          <div className="col-md-6">
                            <h6>Recommended Adjustments:</h6>
                            <div className="adjustment-suggestions">
                              {analysis.score_adjustments?.map((adj, index) => (
                                <div key={index} className="adjustment-item">
                                  <span className="fw-semibold">{adj.component}:</span>
                                  <span className={`badge bg-${adj.impact > 0 ? 'danger' : adj.impact < 0 ? 'success' : 'secondary'} ms-2`}>
                                    {adj.impact > 0 ? '+' : ''}{adj.impact}
                                  </span>
                                  <small className="text-muted d-block">{adj.reason}</small>
                                </div>
                              ))}
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Adjusted Scores */}
                {adjustedScores && (
                  <div className="col-12 mb-4">
                    <div className="card">
                      <div className="card-header bg-success text-white">
                        <h6 className="mb-0">
                          <FaShieldAlt className="me-2" />
                          Adjusted Scores
                        </h6>
                      </div>
                      <div className="card-body">
                        <div className="score-comparison">
                          <div className="row">
                            {Object.entries(currentScores).map(([key, value]) => (
                              <div key={key} className="col-md-6 mb-3">
                                <div className="score-comparison-item">
                                  <div className="original-score">
                                    <small className="text-muted">Original</small>
                                    <span className="fw-bold">{value}</span>
                                  </div>
                                  <div className="arrow">→</div>
                                  <div className="adjusted-score">
                                    <small className="text-muted">Adjusted</small>
                                    <span className={`fw-bold text-${getScoreColor(adjustedScores[key])}`}>
                                      {adjustedScores[key]}
                                    </span>
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                        
                        <div className="mt-4 text-center">
                          <button
                            className="btn btn-success btn-lg"
                            onClick={saveAdjustments}
                            disabled={loading}
                          >
                            {loading ? (
                              <>
                                <div className="spinner-border spinner-border-sm me-2" role="status"></div>
                                Saving...
                              </>
                            ) : (
                              <>
                                <FaSave className="me-2" />
                                Save Adjustments
                              </>
                            )}
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

    <style jsx>{`
        .score-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 1rem;
        }
        
        .score-item {
          padding: 1rem;
          border: 1px solid #dee2e6;
          border-radius: 0.375rem;
          background: #f8f9fa;
        }
        
        .form-range {
          width: 100%;
          margin-top: 0.5rem;
        }
        
        .detected-keywords {
          background: #fff3cd;
          border: 1px solid #ffeaa7;
          border-radius: 0.375rem;
          padding: 1rem;
        }
        
        .keyword-list {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
        }
        
        .risk-factors {
          list-style: none;
          padding: 0;
        }
        
        .risk-factors li {
          padding: 0.5rem 0;
          border-left: 3px solid #ffc107;
          background: #fff;
          margin-bottom: 0.5rem;
        }
        
        .adjustment-suggestions {
          background: #d1ecf1;
          border: 1px solid #bee5eb;
          border-radius: 0.375rem;
          padding: 1rem;
        }
        
        .adjustment-item {
          padding: 0.5rem 0;
          border-bottom: 1px solid #dee2e6;
        }
        
        .score-comparison {
          background: #f8f9fa;
          border: 1px solid #dee2e6;
          border-radius: 0.375rem;
          padding: 1rem;
        }
        
        .score-comparison-item {
          display: flex;
          align-items: center;
          padding: 0.5rem;
        }
        
        .original-score, .adjusted-score {
          flex: 1;
          text-align: center;
        }
        
        .arrow {
          font-size: 1.5rem;
          font-weight: bold;
          margin: 0 0.5rem;
          color: #6c757d;
        }
        
        .spin-animation {
          animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
  );
};

export default OfficerPortal;
