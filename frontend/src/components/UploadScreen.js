import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { toast } from 'react-hot-toast';
import axios from 'axios';
import { 
  FaCloudUploadAlt, 
  FaFileAlt, 
  FaCheckCircle, 
  FaExclamationTriangle,
  FaSpinner,
  FaTrash
} from 'react-icons/fa';

const UploadScreen = () => {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [jobId, setJobId] = useState(null);

  const onDrop = useCallback((acceptedFiles) => {
    const newFiles = acceptedFiles.map(file => ({
      file,
      id: Math.random().toString(36).substr(2, 9),
      type: getDocumentType(file.name),
      uploaded: false
    }));
    
    setFiles(prev => [...prev, ...newFiles]);
    toast.success(`${newFiles.length} file(s) added`);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png'],
      'image/tiff': ['.tiff', '.tif']
    },
    maxSize: 50 * 1024 * 1024, // 50MB
    multiple: true
  });

  const getDocumentType = (filename) => {
    const ext = filename.split('.').pop().toLowerCase();
    const typeMap = {
      'pdf': 'financial_statement',
      'xlsx': 'financial_statement',
      'xls': 'financial_statement',
      'jpg': 'bank_statement',
      'jpeg': 'bank_statement',
      'png': 'bank_statement',
      'tiff': 'bank_statement',
      'tif': 'bank_statement'
    };
    return typeMap[ext] || 'other';
  };

  const removeFile = (id) => {
    setFiles(prev => prev.filter(file => file.id !== id));
  };

  const handleUpload = async () => {
    if (files.length === 0) {
      toast.error('Please select files to upload');
      return;
    }

    setUploading(true);
    setUploadProgress(0);

    try {
      const formData = new FormData();
      const documentTypes = files.map(f => f.type);
      
      files.forEach(fileObj => {
        formData.append('files', fileObj.file);
      });
      
      formData.append('document_types', JSON.stringify(documentTypes));

      const response = await axios.post('/api/ingest', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          const progress = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          setUploadProgress(progress);
        },
      });

      if (response.data.job_id) {
        setJobId(response.data.job_id);
        toast.success('Documents uploaded successfully!');
        
        // Reset after successful upload
        setTimeout(() => {
          setFiles([]);
          setUploadProgress(0);
          setUploading(false);
        }, 2000);
      }
    } catch (error) {
      console.error('Upload error:', error);
      toast.error(error.response?.data?.detail || 'Upload failed');
      setUploading(false);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="upload-screen container-fluid py-4">
      <div className="row justify-content-center">
        <div className="col-lg-8">
          <div className="card shadow-sm">
            <div className="card-header bg-primary text-white">
              <h4 className="mb-0">
                <FaCloudUploadAlt className="me-2" />
                Document Upload
              </h4>
            </div>
            <div className="card-body">
              {/* Upload Area */}
              <div
                {...getRootProps()}
                className={`upload-area p-4 text-center border-2 border-dashed rounded mb-4 ${
                  isDragActive ? 'border-primary bg-light' : 'border-secondary'
                }`}
                style={{ minHeight: '200px', cursor: 'pointer' }}
              >
                <input {...getInputProps()} />
                <FaCloudUploadAlt size={48} className="text-muted mb-3" />
                <h5>
                  {isDragActive
                    ? 'Drop files here...'
                    : 'Drag & drop documents here, or click to select'}
                </h5>
                <p className="text-muted">
                  Supported formats: PDF, Excel, Images (Max 50MB)
                </p>
              </div>

              {/* File List */}
              {files.length > 0 && (
                <div className="file-list mb-4">
                  <h6 className="mb-3">Selected Files:</h6>
                  {files.map(fileObj => (
                    <div
                      key={fileObj.id}
                      className="file-item d-flex justify-content-between align-items-center p-2 mb-2 bg-light rounded"
                    >
                      <div className="d-flex align-items-center">
                        <FaFileAlt className="text-primary me-2" />
                        <div>
                          <div className="fw-semibold">{fileObj.file.name}</div>
                          <small className="text-muted">
                            {formatFileSize(fileObj.file.size)} • {fileObj.type}
                          </small>
                        </div>
                      </div>
                      <button
                        className="btn btn-sm btn-outline-danger"
                        onClick={() => removeFile(fileObj.id)}
                        disabled={uploading}
                      >
                        <FaTrash />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* Upload Progress */}
              {uploading && (
                <div className="upload-progress mb-4">
                  <div className="d-flex align-items-center mb-2">
                    <FaSpinner className="spin-animation me-2" />
                    <span>Uploading documents... {uploadProgress}%</span>
                  </div>
                  <div className="progress">
                    <div
                      className="progress-bar progress-bar-striped progress-bar-animated"
                      style={{ width: `${uploadProgress}%` }}
                    ></div>
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              <div className="d-flex gap-2">
                <button
                  className="btn btn-primary flex-fill"
                  onClick={handleUpload}
                  disabled={files.length === 0 || uploading}
                >
                  {uploading ? (
                    <>
                      <FaSpinner className="spin-animation me-2" />
                      Uploading...
                    </>
                  ) : (
                    <>
                      <FaCloudUploadAlt className="me-2" />
                      Upload Documents
                    </>
                  )}
                </button>
                
                {jobId && (
                  <button
                    className="btn btn-success flex-fill"
                    onClick={() => window.location.href = `/results?jobId=${jobId}`}
                  >
                    <FaCheckCircle className="me-2" />
                    View Results
                  </button>
                )}
              </div>

              {/* Job Status */}
              {jobId && (
                <div className="alert alert-info mt-3">
                  <FaExclamationTriangle className="me-2" />
                  <strong>Processing Started!</strong> Job ID: {jobId}
                  <br />
                  <small>
                    You can track progress in the Results Dashboard.
                  </small>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <style jsx>{`
        .upload-area {
          transition: all 0.3s ease;
        }
        
        .upload-area:hover {
          border-color: #007bff !important;
          background-color: #f8f9fa !important;
        }
        
        .file-item {
          transition: all 0.2s ease;
        }
        
        .file-item:hover {
          background-color: #e9ecef !important;
        }
        
        .spin-animation {
          animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        
        .progress {
          height: 8px;
          border-radius: 4px;
          overflow: hidden;
        }
        
        .progress-bar {
          transition: width 0.3s ease;
        }
      `}</style>
    </div>
  );
};

export default UploadScreen;
