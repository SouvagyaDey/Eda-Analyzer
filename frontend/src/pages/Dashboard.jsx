import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getSessionDetail, getAiInsights, getColumnInfo, generateOnDemandCharts } from '../utils/api';
import { Sparkles, ArrowLeft, Table, BarChart, Download, Loader, Trash2, Grid, List, Maximize2, X } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import './Dashboard.css';

const Dashboard = () => {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [session, setSession] = useState(null);
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(true);
  const [insightsLoading, setInsightsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('library');
  const [selectedChart, setSelectedChart] = useState(null);
  const [columnInfo, setColumnInfo] = useState(null);
  const [viewMode, setViewMode] = useState('grid'); // 'grid' or 'list'
  const [fullscreenChart, setFullscreenChart] = useState(null);
  
  // On-demand chart generation states
  const [xAxis, setXAxis] = useState('');
  const [yAxis, setYAxis] = useState('');
  const [generating, setGenerating] = useState(false);
  const [theme, setTheme] = useState(localStorage.getItem('theme') || 'light');
  const [successMessage, setSuccessMessage] = useState(null);
  const [availablePlots, setAvailablePlots] = useState([]);
  const [selectedPlots, setSelectedPlots] = useState([]);

  useEffect(() => {
    loadSessionData();
  }, [sessionId]);

  useEffect(() => {
    // Auto-select first chart when charts are loaded
    if (session?.charts && session.charts.length > 0 && !selectedChart) {
      setSelectedChart(session.charts[0]);
    }
  }, [session]);

  const loadSessionData = async () => {
    try {
      setLoading(true);
      const data = await getSessionDetail(sessionId);
      setSession(data);
      
      // Load column info
      try {
        const colInfo = await getColumnInfo(sessionId);
        setColumnInfo(colInfo);
      } catch (colErr) {
        console.warn('Could not load column info:', colErr);
      }
      
      // Load insights if they exist
      if (data.insights) {
        setInsights(data.insights);
      }
    } catch (err) {
      setError('Failed to load session data');
      console.error('Error loading session:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateInsights = async () => {
    try {
      setInsightsLoading(true);
      const data = await getAiInsights(sessionId);
      setInsights(data.insights);
      setActiveTab('insights');
    } catch (err) {
      setError('Failed to generate insights');
      console.error('Error generating insights:', err);
    } finally {
      setInsightsLoading(false);
    }
  };

  // Determine available plot types based on X and Y axis selection
  const updateAvailablePlots = (x, y) => {
    if (!x && !y) {
      setAvailablePlots([]);
      setSelectedPlots([]);
      return;
    }

    // Check if "All Columns" is selected
    const isAllX = x === '__all__';
    const isAllY = y === '__all__';
    
    const numericCount = columnInfo?.numeric_columns?.length || 0;
    
    let plots = [];

    // If "All Columns" is selected, show only overview plots
    if (isAllX || isAllY) {
      plots = [];
      if (numericCount >= 2) {
        plots.push(
          { id: 'correlation_heatmap', name: 'Correlation Heatmap' },
          { id: 'pairplot', name: 'Pair Plot' }
        );
      }
      // Always add Missing Values for overview
      plots.push({ id: 'missing_values', name: 'Missing Values' });
      
      setAvailablePlots(plots);
      setSelectedPlots(plots.map(p => p.id));
      return;
    }

    const xCol = columnInfo?.columns.find(c => c.name === x);
    const yCol = columnInfo?.columns.find(c => c.name === y);
    
    const xIsNumeric = xCol?.type === 'numeric';
    const yIsNumeric = yCol?.type === 'numeric';

    if (x && y) {
      // Both axes selected
      if (xIsNumeric && yIsNumeric) {
        // Numeric x Numeric: scatter, line, and bar chart
        plots = [
          { id: 'scatter', name: 'Scatter Plot' },
          { id: 'line', name: 'Line Plot' },
          { id: 'bar_chart', name: 'Bar Chart' }
        ];
      } else {
        // Any categorical: bar chart
        plots = [
          { id: 'bar_chart', name: 'Bar Chart' }
        ];
      }
    } else if (x || y) {
      // Single axis selected
      const col = xCol || yCol;
      if (col?.type === 'numeric') {
        // Single numeric: histogram, boxplot, distribution only
        plots = [
          { id: 'histogram', name: 'Histogram' },
          { id: 'boxplot', name: 'Box Plot' },
          { id: 'distribution', name: 'Distribution' }
        ];
      } else if (col?.type === 'categorical') {
        // Single categorical: bar chart only
        plots = [
          { id: 'bar_chart', name: 'Bar Chart' }
        ];
      }
    }

    setAvailablePlots(plots);
    setSelectedPlots(plots.map(p => p.id)); // Auto-select all available plots
  };

  const handleXAxisChange = (value) => {
    setXAxis(value);
    updateAvailablePlots(value, yAxis);
  };

  const handleYAxisChange = (value) => {
    setYAxis(value);
    updateAvailablePlots(xAxis, value);
  };

  const handlePlotToggle = (plotType) => {
    setSelectedPlots(prev => 
      prev.includes(plotType) 
        ? prev.filter(p => p !== plotType)
        : [...prev, plotType]
    );
  };

  useEffect(() => {
    // Initialize available plots when component mounts
    if (columnInfo) {
      updateAvailablePlots(xAxis, yAxis);
    }
  }, [columnInfo]);

  const handleGenerateCharts = async () => {
    if (!xAxis && !yAxis) {
      alert('Please select at least one axis (X or Y)');
      return;
    }

    if (selectedPlots.length === 0) {
      setError('Please select at least one plot type');
      return;
    }

    try {
      setGenerating(true);
      setError(null);
      setSuccessMessage(null);
      
      // Convert "__all__" to null for backend
      const xAxisValue = xAxis === '__all__' ? null : xAxis;
      const yAxisValue = yAxis === '__all__' ? null : yAxis;
      
      // Filter selectedPlots to only include plots that are currently available
      const validPlots = selectedPlots.filter(plot => 
        availablePlots.some(ap => ap.id === plot)
      );
      
      // Send 'all' to backend to generate ALL possible plots
      const result = await generateOnDemandCharts(
        sessionId,
        xAxisValue || null,
        yAxisValue || null,
        validPlots.length === availablePlots.length ? ['all'] : validPlots, // If all selected, send ['all']
        theme
      );

      if (result.charts_generated === false && result.message) {
        // All charts already exist
        setSuccessMessage(`${result.message} Check the Generated Charts section below.`);
        setTimeout(() => setSuccessMessage(null), 5000);
        return;
      }

      if (result.charts_generated && result.charts.length > 0) {
        // Reload session to get updated charts list
        await loadSessionData();
        
        setActiveTab('charts');
        
        // Show appropriate message based on what was generated
        if (result.newly_generated === 0) {
          setSuccessMessage('These plots are already in your library!');
        } else if (result.message) {
          setSuccessMessage(`✓ ${result.message}`);
        } else {
          setSuccessMessage(`✓ Generated ${result.charts.length} chart(s): ${selectedPlots.join(', ')}`);
        }
        
        // Auto-hide success message after 5 seconds
        setTimeout(() => setSuccessMessage(null), 5000);
      } else {
        setError('No charts were generated. Try different axis selections.');
      }
    } catch (err) {
      setError('Failed to generate charts: ' + (err.response?.data?.error || err.message));
      console.error('Error generating charts:', err);
    } finally {
      setGenerating(false);
    }
  };

  const handleDeleteChart = async (chartId) => {
    if (!confirm('Are you sure you want to delete this chart?')) {
      return;
    }

    try {
      // Call delete API (you'll need to add this endpoint)
      // For now, we'll just reload and filter it out locally
      const updatedCharts = session.charts.filter(c => c.id !== chartId);
      setSession({ ...session, charts: updatedCharts });
      
      if (selectedChart?.id === chartId) {
        setSelectedChart(updatedCharts[0] || null);
      }
      
      setSuccessMessage('✓ Chart deleted successfully');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setError('Failed to delete chart: ' + err.message);
      console.error('Error deleting chart:', err);
    }
  };

  const handleDownloadChart = async (chart) => {
    try {
      const chartUrl = getChartUrl(chart);
      const response = await fetch(chartUrl);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${chart.chart_type}_${chart.column_name || 'chart'}.png`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Error downloading chart:', err);
      setError('Failed to download chart');
    }
  };

  // Helper to get chart URL from path
  const getChartUrl = (chart) => {
    if (chart.chart_url) return chart.chart_url;
    if (chart.chart_path) {
      // chart_path format: "eda_outputs/session-id/chart.png"
      return `http://localhost:8000/${chart.chart_path}`;
    }
    return '';
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p className="loading-text">Loading EDA results...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container">
        <div className="error-message">{error}</div>
        <button onClick={() => navigate('/')} className="btn btn-primary">
          <ArrowLeft size={20} />
          Back to Home
        </button>
      </div>
    );
  }

  if (!session) {
    return null;
  }

  return (
    <div className="dashboard-page">
      <div className="container-fluid">
        {/* Header */}
        <div className="dashboard-header-modern">
          <div className="header-left">
            <button onClick={() => navigate('/')} className="back-btn-modern">
              <ArrowLeft size={20} />
              <span>Back to Home</span>
            </button>
            <div className="header-divider"></div>
            <div className="dataset-info">
              <div className="dataset-icon"><BarChart size={24} /></div>
              <div>
                <h1 className="dataset-name">{session.filename}</h1>
                <div className="dataset-meta">
                  <span className="meta-badge">
                    <Table size={14} />
                    {session.row_count?.toLocaleString()} rows
                  </span>
                  <span className="meta-badge">
                    <BarChart size={14} />
                    {session.column_count} columns
                  </span>
                  <span className="meta-badge chart-count">
                    {session.charts?.length || 0} charts
                  </span>
                </div>
              </div>
            </div>
          </div>
          <div className="header-right">
            <button
              onClick={() => {
                if (insights) {
                  setActiveTab('insights');
                } else {
                  handleGenerateInsights();
                }
              }}
              className="btn-insights-header"
              disabled={insightsLoading}
            >
              <Sparkles size={18} />
              {insightsLoading ? 'Generating...' : insights ? 'View Insights' : 'Generate AI Insights'}
            </button>
          </div>
        </div>

        {/* Main Content with Sidebar */}
        <div className="dashboard-layout">
          {/* Sidebar */}
          <div className="sidebar">
            {/* Chart Generator Section */}
            {columnInfo && (
              <div className="sidebar-generator-modern">
                <div className="generator-header">
                  <div className="generator-icon"><BarChart size={20} /></div>
                  <h3 className="generator-title">Chart Generator</h3>
                </div>
                <div className="generator-controls-vertical">
                  <div className="axis-selector">
                    <label htmlFor="x-axis-select">X-Axis:</label>
                    <select
                      id="x-axis-select"
                      value={xAxis}
                      onChange={(e) => handleXAxisChange(e.target.value)}
                      className="axis-select"
                      disabled={generating}
                    >
                      <option value="">-- None --</option>
                      <option value="__all__">📊 All Columns (Overview)</option>
                      {columnInfo.columns.map((col) => (
                        <option key={col.name} value={col.name}>
                          {col.name} ({col.type})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="axis-selector">
                    <label htmlFor="y-axis-select">Y-Axis:</label>
                    <select
                      id="y-axis-select"
                      value={yAxis}
                      onChange={(e) => handleYAxisChange(e.target.value)}
                      className="axis-select"
                      disabled={generating}
                    >
                      <option value="">-- None --</option>
                      <option value="__all__">📊 All Columns (Overview)</option>
                      {columnInfo.columns.map((col) => (
                        <option key={col.name} value={col.name}>
                          {col.name} ({col.type})
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Available Plot Types */}
                  {availablePlots.length > 0 && (
                    <div className="plot-type-selector">
                      <label className="plot-selector-label">Available Plots:</label>
                      <div className="plot-checkboxes">
                        {availablePlots.map(plot => (
                          <label 
                            key={plot.id} 
                            className="plot-checkbox-label"
                          >
                            <input
                              type="checkbox"
                              checked={selectedPlots.includes(plot.id)}
                              onChange={() => handlePlotToggle(plot.id)}
                              disabled={generating}
                            />
                            <span className="plot-type-name">
                              {plot.name}
                              {(plot.id === 'correlation_heatmap' || plot.id === 'pairplot' || plot.id === 'missing_values') && 
                                <span className="plot-info-icon">ⓘ</span>
                              }
                            </span>
                          </label>
                        ))}
                      </div>
                    </div>
                  )}

                  <button
                    onClick={handleGenerateCharts}
                    className="btn btn-primary generate-btn-vertical"
                    disabled={generating || (!xAxis && !yAxis)}
                  >
                    {generating ? (
                      <>
                        <Loader size={18} className="spinner" />
                        Generating...
                      </>
                    ) : (
                      <>
                        <BarChart size={18} />
                        Generate
                      </>
                    )}
                  </button>
                  
                  {error && (
                    <div className="generator-error-small">
                      {error}
                    </div>
                  )}
                  
                  {successMessage && (
                    <div className="generator-success-small">
                      {successMessage}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Main Content Area */}
          <div className="main-content">
            {/* Plot Library View with Thumbnails */}
            {activeTab === 'library' && (
              <div className="plot-viewer-container fade-in">
                {selectedChart ? (
                  <>
                    {/* Main Plot Display */}
                    <div className="main-plot-display">
                      <div className="plot-display-header">
                        <div className="plot-display-info">
                          <span className="plot-type-badge-large">{selectedChart.chart_type}</span>
                          <h2 className="plot-display-title">
                            {formatChartTitle(selectedChart.chart_type, selectedChart.column_name)}
                          </h2>
                        </div>
                        <div className="plot-display-actions">
                          <button
                            onClick={() => handleDownloadChart(selectedChart)}
                            className="action-btn-modern download"
                          >
                            <Download size={18} />
                            <span>Download</span>
                          </button>
                          <button
                            onClick={() => setFullscreenChart(selectedChart)}
                            className="action-btn-modern fullscreen"
                          >
                            <Maximize2 size={18} />
                            <span>Fullscreen</span>
                          </button>
                          <button
                            onClick={() => handleDeleteChart(selectedChart.id)}
                            className="action-btn-modern delete"
                          >
                            <Trash2 size={18} />
                            <span>Delete</span>
                          </button>
                        </div>
                      </div>
                      <div className="plot-display-body">
                        <img
                          src={getChartUrl(selectedChart)}
                          alt={formatChartTitle(selectedChart.chart_type, selectedChart.column_name)}
                          className="main-plot-image"
                          onError={(e) => {
                            console.error('Failed to load chart:', getChartUrl(selectedChart));
                            e.target.alt = 'Failed to load chart';
                          }}
                        />
                      </div>
                    </div>

                    {/* Thumbnail Strip */}
                    {session.charts && session.charts.length > 1 && (
                      <div className="thumbnail-strip">
                        <div className="thumbnail-strip-header">
                          <span className="thumbnail-label">All Plots ({session.charts.length})</span>
                        </div>
                        <div className="thumbnail-grid">
                          {session.charts.map((chart) => (
                            <div
                              key={chart.id}
                              className={`thumbnail-item ${selectedChart?.id === chart.id ? 'active' : ''}`}
                              onClick={() => setSelectedChart(chart)}
                            >
                              <img
                                src={getChartUrl(chart)}
                                alt={formatChartTitle(chart.chart_type, chart.column_name)}
                                className="thumbnail-img"
                                onError={(e) => {
                                  e.target.style.display = 'none';
                                  e.target.parentElement.classList.add('error');
                                }}
                              />
                              <div className="thumbnail-overlay">
                                <span className="thumbnail-type">{chart.chart_type}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="empty-plot-viewer">
                    <BarChart size={80} className="empty-icon" />
                    <h3>Select a plot to view</h3>
                    <p>Choose a plot from the sidebar to display it here</p>
                  </div>
                )}
              </div>
            )}

            {/* Fullscreen Modal */}
            {fullscreenChart && (
              <div className="fullscreen-modal" onClick={() => setFullscreenChart(null)}>
                <div className="fullscreen-content" onClick={(e) => e.stopPropagation()}>
                  <div className="fullscreen-header">
                    <div>
                      <span className="fullscreen-badge">{fullscreenChart.chart_type}</span>
                      <h2 className="fullscreen-title">
                        {formatChartTitle(fullscreenChart.chart_type, fullscreenChart.column_name)}
                      </h2>
                    </div>
                    <div className="fullscreen-actions">
                      <button
                        onClick={() => handleDownloadChart(fullscreenChart)}
                        className="fullscreen-btn"
                      >
                        <Download size={20} />
                        Download
                      </button>
                      <button
                        onClick={() => setFullscreenChart(null)}
                        className="fullscreen-btn close"
                      >
                        <X size={20} />
                      </button>
                    </div>
                  </div>
                  <div className="fullscreen-body">
                    <img
                      src={getChartUrl(fullscreenChart)}
                      alt={formatChartTitle(fullscreenChart.chart_type, fullscreenChart.column_name)}
                      className="fullscreen-image"
                    />
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'charts' && selectedChart && (
              <>
                <div className="chart-view-modern fade-in">
                  <div className="chart-view-header-modern">
                    <button 
                      onClick={() => {
                        setSelectedChart(null);
                        setActiveTab('library');
                      }} 
                      className="back-btn-modern"
                      style={{marginRight: '16px'}}
                    >
                      <ArrowLeft size={20} />
                      <span>Back to Library</span>
                    </button>
                    <div className="chart-header-left">
                      <div className="chart-type-badge">{selectedChart.chart_type}</div>
                      <h2 className="chart-title">{formatChartTitle(selectedChart.chart_type, selectedChart.column_name)}</h2>
                    </div>
                    <div className="chart-actions-modern">
                      <button
                        onClick={() => handleDownloadChart(selectedChart)}
                        className="btn-action-modern btn-download"
                        title="Download Chart"
                      >
                        <Download size={18} />
                        <span>Download</span>
                      </button>
                      <button
                        onClick={() => setFullscreenChart(selectedChart)}
                        className="btn-action-modern btn-fullscreen"
                        title="Fullscreen"
                      >
                        <Maximize2 size={18} />
                        <span>Fullscreen</span>
                      </button>
                      <button
                        onClick={() => handleDeleteChart(selectedChart.id)}
                        className="btn-action-modern btn-delete"
                        title="Delete Chart"
                      >
                        <Trash2 size={18} />
                        <span>Delete</span>
                      </button>
                  </div>
                </div>
                <div className="chart-view-body">
                    <img
                      src={getChartUrl(selectedChart)}
                      alt={selectedChart.chart_type}
                      className="chart-view-image"
                      onError={(e) => {
                        console.error('Failed to load chart:', getChartUrl(selectedChart));
                        e.target.alt = 'Failed to load chart';
                      }}
                    />
                  </div>
                </div>

                {/* Thumbnail Strip for Charts Tab */}
                {session.charts && session.charts.length > 1 && (
                  <div className="thumbnail-strip">
                    <div className="thumbnail-strip-header">
                      <span className="thumbnail-label">All Plots ({session.charts.length})</span>
                    </div>
                    <div className="thumbnail-grid">
                      {session.charts.map((chart) => (
                        <div
                          key={chart.id}
                          className={`thumbnail-item ${selectedChart?.id === chart.id ? 'active' : ''}`}
                          onClick={() => setSelectedChart(chart)}
                        >
                          <img
                            src={getChartUrl(chart)}
                            alt={formatChartTitle(chart.chart_type, chart.column_name)}
                            className="thumbnail-img"
                            onError={(e) => {
                              e.target.style.display = 'none';
                              e.target.parentElement.classList.add('error');
                            }}
                          />
                          <div className="thumbnail-overlay">
                            <span className="thumbnail-type">{chart.chart_type}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}            {activeTab === 'insights' && (
              <div className="insights-view fade-in">
                {insights ? (
                  <div className="insights-card-modern">
                    <div className="insights-header-modern">
                      <button 
                        onClick={() => setActiveTab('library')} 
                        className="back-btn-modern"
                        style={{marginBottom: '16px'}}
                      >
                        <ArrowLeft size={20} />
                        <span>Back to Library</span>
                      </button>
                      <div className="insights-icon-wrapper">
                        <Sparkles size={24} />
                      </div>
                      <div>
                        <h2>AI-Powered Data Analysis</h2>
                        <p className="insights-subtitle">Intelligent insights generated by Gemini AI</p>
                      </div>
                    </div>
                    <div className="insights-content">
                      <ReactMarkdown 
                        remarkPlugins={[remarkGfm]}
                        rehypePlugins={[rehypeRaw]}
                        components={{
                          img: ({node, ...props}) => (
                            <img
                              {...props}
                              src={props.src?.startsWith('http') ? props.src : `http://localhost:8000${props.src}`}
                              style={{maxWidth: '100%', height: 'auto', margin: '20px 0', borderRadius: '8px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)'}}
                              alt={props.alt || 'Chart visualization'}
                            />
                          )
                        }}
                      >
                        {insights}
                      </ReactMarkdown>
                    </div>
                  </div>
                ) : (
                  <div className="empty-state">
                    <Sparkles size={64} />
                    <p>Generating AI insights...</p>
                    <div className="loading-spinner"></div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'charts' && !selectedChart && (
              <div className="empty-state">
                <BarChart size={64} />
                <p>Select a chart from the sidebar</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// Helper function to format chart titles
const formatChartTitle = (chartType, columnName) => {
  const typeMap = {
    histogram: 'Histogram',
    bar: 'Bar Chart',
    bar_chart: 'Bar Chart',
    correlation: 'Correlation Heatmap',
    correlation_heatmap: 'Correlation Heatmap',
    pairplot: 'Pair Plot',
    boxplot: 'Box Plot',
    missing: 'Missing Values',
    missing_values: 'Missing Values',
    scatter: 'Scatter Plot',
    distribution: 'Distribution Plot',
    line: 'Line Plot',
  };

  const title = typeMap[chartType] || chartType;
  return columnName ? `${title}: ${columnName}` : title;
};

export default Dashboard;
