import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import axios from 'axios';
import {
  FaChartRadar,
  FaChartLine,
  FaExclamationTriangle,
  FaCheckCircle,
  FaTimesCircle,
  FaClock,
  FaDownload,
  FaFileAlt,
  FaSpinner,
  FaEye
} from 'react-icons/fa';
import { Radar, Line } from 'react-chartjs-2';

const ResultsDashboard = () => {
  const { jobId } = useParams();
  const navigate = useNavigate();
  
  const [loading, setLoading] = useState(true);
  const [jobData, setJobData] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    if (jobId) {
      fetchJobStatus();
    }
  }, [jobId]);

  const fetchJobStatus = async () => {
    try {
      const response = await axios.get(`/api/jobs/${jobId}/status`);
      setJobData(response.data);
    } catch (error) {
      console.error('Error fetching job status:', error);
      toast.error('Failed to fetch job status');
    } finally {
      setLoading(false);
    }
  };

  const refreshStatus = async () => {
    setRefreshing(true);
    await fetchJobStatus();
    setRefreshing(false);
  };

  const downloadCAM = async () => {
    try {
      const response = await axios.get(`/api/scoring/cam/${jobId}`, {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.download = `CAM_${jobId}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success('CAM downloaded successfully');
    } catch (error) {
      console.error('Download error:', error);
      toast.error('Failed to download CAM');
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      'pending': 'warning',
      'running': 'info',
      'completed': 'success',
      'failed': 'danger',
      'cancelled': 'secondary'
    };
    return colors[status] || 'secondary';
  };

  const getStatusIcon = (status) => {
    const icons = {
      'pending': <FaClock />,
      'running': <FaSpinner className="spin-animation" />,
      'completed': <FaCheckCircle />,
      'failed': <FaTimesCircle />,
      'cancelled': <FaTimesCircle />
    };
    return icons[status] || <FaClock />;
  };

  if (loading) {
    return (
      <div className="text-center py-5">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading...</span>
        </div>
        <p className="mt-3">Loading job status...</p>
      </div>
    );
  }

  const radarData = jobData?.decision?.credit_decision?.five_c_scores ? {
    labels: ['Character', 'Capacity', 'Capital', 'Collateral', 'Conditions'],
    datasets: [{
      label: 'Five Cs Scores',
      data: [
        jobData.decision.credit_decision.five_c_scores.character,
        jobData.decision.credit_decision.five_c_scores.capacity,
        jobData.decision.credit_decision.five_c_scores.capital,
        jobData.decision.credit_decision.five_c_scores.collateral,
        jobData.decision.credit_decision.five_c_scores.conditions
      ],
      backgroundColor: [
        'rgba(255, 99, 132, 0.2)',
        'rgba(54, 162, 235, 0.2)',
        'rgba(255, 206, 86, 0.2)',
        'rgba(75, 192, 192, 0.2)',
        'rgba(153, 102, 255, 0.2)'
      ],
      borderColor: [
        'rgba(255, 99, 132, 1)',
        'rgba(54, 162, 235, 1)',
        'rgba(255, 206, 86, 1)',
        'rgba(75, 192, 192, 1)',
        'rgba(153, 102, 255, 1)'
      ],
      borderWidth: 2
    }]
  } : null;

  const radarOptions = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      r: {
        beginAtZero: true,
        max: 100,
        ticks: {
          stepSize: 20
        }
      }
    },
    plugins: {
      legend: {
        position: 'top'
      }
    }
  };

  // Create a wrapper component for the results section
  const ResultsSection = () => {
    if (!jobData?.status === 'completed' || !jobData?.decision?.credit_decision) {
      return null;
    }

    return (
      <div className="row mt-4">
        <div className="col-lg-6 mb-4">
          <div className="card shadow-sm">
            <div className="card-header">
              <h5 className="mb-0">
                <FaChartRadar className="me-2" />
                Five Cs Analysis
              </h5>
            </div>
            <div className="card-body">
              {radarData && <Radar data={radarData} options={radarOptions} />}
            </div>
          </div>
        </div>

        <div className="col-lg-6 mb-4">
          <div className="card shadow-sm">
            <div className="card-header">
              <h5 className="mb-0">
                <FaChartLine className="me-2" />
                Credit Decision
              </h5>
            </div>
            <div className="card-body">
              <div className="decision-summary">
                <div className="row text-center mb-3">
                  <div className="col-6">
                    <h3 className="text-primary">
                      {jobData.decision.credit_decision.total_score?.toFixed(1)}
                    </h3>
                    <p className="text-muted">Total Score</p>
                  </div>
                  <div className="col-6">
                    <span className={`badge fs-6 p-2 bg-${jobData.decision.credit_decision.grade?.toLowerCase().replace('_', '-')}`}>
                      {jobData.decision.credit_decision.grade?.replace('_', ' ')}
                    </span>
                    <p className="text-muted">Credit Grade</p>
                  </div>
                </div>
                
                <div className="loan-limits">
                  <h6 className="mb-3">Loan Limits:</h6>
                  <div className="row g-2">
                    <div className="col-6">
                      <small className="text-muted">Cash Flow Ceiling</small>
                      <div className="fw-semibold">
                        ₹{jobData.decision.credit_decision.loan_limit?.cash_flow_ceiling?.toLocaleString('en-IN')}
                      </div>
                    </div>
                    <div className="col-6">
                      <small className="text-muted">Asset Ceiling</small>
                      <div className="fw-semibold">
                        ₹{jobData.decision.credit_decision.loan_limit?.asset_ceiling?.toLocaleString('en-IN')}
                      </div>
                    </div>
                    <div className="col-6">
                      <small className="text-muted">Sector Ceiling</small>
                      <div className="fw-semibold">
                        ₹{jobData.decision.credit_decision.loan_limit?.sector_ceiling?.toLocaleString('en-IN')}
                      </div>
                    </div>
                    <div className="col-6">
                      <small className="text-muted">Final Limit</small>
                      <div className="fw-bold text-success">
                        ₹{jobData.decision.credit_decision.loan_limit?.final_limit?.toLocaleString('en-IN')}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="results-dashboard container-fluid py-4">
      <div className="row">
        {/* Job Status Card */}
        <div className="col-lg-4 mb-4">
          <div className="card shadow-sm">
            <div className="card-header d-flex justify-content-between align-items-center">
              <h5 className="mb-0">
                <FaClock className="me-2" />
                Job Status
              </h5>
              <button
                className="btn btn-sm btn-outline-primary"
                onClick={refreshStatus}
                disabled={refreshing}
              >
                {refreshing ? (
                  <FaSpinner className="spin-animation" />
                ) : (
                  'Refresh'
                )}
              </button>
            </div>
            <div className="card-body text-center">
              <div className={`status-indicator mb-3 text-${getStatusColor(jobData?.status)}`}>
                <div className="status-icon mb-2">
                  {getStatusIcon(jobData?.status)}
                </div>
                <h4 className="mb-1">{jobData?.status?.toUpperCase()}</h4>
                <p className="text-muted mb-0">Job ID: {jobId}</p>
              </div>
              
              <div className="progress-info">
                <div className="d-flex justify-content-between mb-2">
                  <span>Progress</span>
                  <span>{Math.round(jobData?.progress || 0)}%</span>
                </div>
                <div className="progress">
                  <div
                    className="progress-bar"
                    style={{
                      width: `${jobData?.progress || 0}%`,
                      backgroundColor: `var(--bs-${getStatusColor(jobData?.status)})`
                    }}
                  ></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="col-lg-8 mb-4">
          <div className="card shadow-sm">
            <div className="card-header">
              <h5 className="mb-0">
                <FaFileAlt className="me-2" />
                Quick Actions
              </h5>
            </div>
            <div className="card-body">
              <div className="row g-3">
                <div className="col-md-4">
                  <button
                    className="btn btn-outline-primary w-100 h-100"
                    onClick={() => navigate('/portal')}
                    disabled={jobData?.status !== 'completed'}
                  >
                    <FaEye className="me-2" />
                    Officer Portal
                  </button>
                </div>
                <div className="col-md-4">
                  <button
                    className="btn btn-outline-success w-100 h-100"
                    onClick={downloadCAM}
                    disabled={jobData?.status !== 'completed'}
                  >
                    <FaDownload className="me-2" />
                    Download CAM
                  </button>
                </div>
                <div className="col-md-4">
                  <button
                    className="btn btn-outline-info w-100 h-100"
                    onClick={() => navigate(`/preview?jobId=${jobId}`)}
                    disabled={jobData?.status !== 'completed'}
                  >
                    <FaEye className="me-2" />
                    Preview CAM
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Results Section */}
      <ResultsSection />

      {/* Task Details */}
      {jobData?.tasks && jobData.tasks.length > 0 && (
        <div className="row mt-4">
          <div className="col-12">
            <div className="card shadow-sm">
              <div className="card-header">
                <h5 className="mb-0">
                  <FaClock className="me-2" />
                  Task Progress Details
                </h5>
              </div>
              <div className="card-body">
                <div className="task-timeline">
                  {jobData.tasks.map((task, index) => (
                    <div key={task.task_id} className="task-item">
                      <div className="d-flex justify-content-between align-items-start">
                        <div className="flex-grow-1">
                          <div className="d-flex align-items-center mb-2">
                            <span className={`task-status-indicator bg-${getStatusColor(task.status)}`}></span>
                            <h6 className="mb-0 ms-2">{task.task_name}</h6>
                          </div>
                          <small className="text-muted">
                            {task.started_at && new Date(task.started_at).toLocaleString()}
                          </small>
                        </div>
                        <div className="text-end">
                          <span className={`badge bg-${getStatusColor(task.status)}`}>
                            {task.status}
                          </span>
                          <div className="text-muted small">
                            {task.progress?.toFixed(1)}%
                          </div>
                        </div>
                      </div>
                      {task.error_message && (
                        <div className="alert alert-danger mt-2 mb-0">
                          <FaExclamationTriangle className="me-2" />
                          {task.error_message}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>

    <style jsx>{`
        .status-indicator {
          padding: 2rem;
          border-radius: 50%;
          width: 120px;
          height: 120px;
          margin: 0 auto;
          display: flex;
          align-items: center;
          justify-content: center;
          background: rgba(0, 0, 0, 0.05);
          border: 2px solid var(--bs-primary);
        }
        
        .status-icon {
          font-size: 2rem;
        }
        
        .task-item {
          padding: 1rem;
          border-left: 3px solid #dee2e6;
          margin-bottom: 1rem;
          background: #f8f9fa;
          border-radius: 0.375rem;
        }
        
        .task-status-indicator {
          width: 12px;
          height: 12px;
          border-radius: 50%;
          display: inline-block;
        }
        
        .spin-animation {
          animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        
        .decision-summary {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          padding: 1.5rem;
          border-radius: 0.5rem;
        }
        
        .loan-limits {
          background: rgba(255, 255, 255, 0.1);
          padding: 1rem;
          border-radius: 0.375rem;
          margin-top: 1rem;
        }
      `}</style>
  );
};

export default ResultsDashboard;
