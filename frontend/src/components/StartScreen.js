import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { FaMicrophone, FaComments, FaRobot, FaCode } from 'react-icons/fa';
import LoadingSpinner from './LoadingSpinner';

const StartContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  text-align: center;
  padding: 40px 20px;
`;

const WelcomeCard = styled.div`
  background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
  border: 2px solid #e0e0e0;
  border-radius: 20px;
  padding: 40px;
  max-width: 900px; /* Increased width for a wider start screen */
  width: 100%;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;

  &:hover {
    box-shadow: 0 12px 48px rgba(0, 0, 0, 0.15);
    transform: translateY(-2px);
  }
`;

const WelcomeIcon = styled.div`
  width: 80px;
  height: 80px;
  background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 24px;
  color: white;
  font-size: 36px;
  box-shadow: 0 8px 24px rgba(220, 53, 69, 0.3);
`;

const WelcomeTitle = styled.h2`
  font-size: 28px;
  font-weight: 700;
  color: #2c3e50;
  margin: 0 0 16px 0;
  letter-spacing: -0.5px;
`;

const WelcomeDescription = styled.p`
  font-size: 18px;
  color: #666;
  line-height: 1.6;
  margin: 0 0 32px 0;
  font-weight: 400;
`;

const FeaturesList = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 20px;
  margin: 32px 0;
`;

const FeatureItem = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 12px;
  border: 1px solid #e0e0e0;
  transition: all 0.3s ease;

  &:hover {
    background: #e9ecef;
    transform: translateY(-2px);
  }
`;

const FeatureIcon = styled.div`
  width: 48px;
  height: 48px;
  background: ${props => props.color || '#007bff'};
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 20px;
  margin-bottom: 12px;
`;

const FeatureTitle = styled.h3`
  font-size: 16px;
  font-weight: 600;
  color: #2c3e50;
  margin: 0 0 8px 0;
`;

const FeatureDescription = styled.p`
  font-size: 14px;
  color: #666;
  margin: 0;
  text-align: center;
  line-height: 1.4;
`;

// Microphone configuration UI styles
const MicConfigContainer = styled.div`
  margin: 24px 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
`;

const MicLabel = styled.label`
  font-size: 16px;
  font-weight: 600;
  color: #2c3e50;
`;

const DeviceSelect = styled.select`
  padding: 8px 12px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  font-size: 16px;
  min-width: 250px;
`;

const StartButton = styled.button`
  background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
  color: white;
  border: none;
  border-radius: 12px;
  padding: 16px 32px;
  font-size: 18px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  box-shadow: 0 4px 16px rgba(220, 53, 69, 0.3);
  min-width: 200px;
  position: relative;
  overflow: hidden;

  &:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(220, 53, 69, 0.4);
  }

  &:active:not(:disabled) {
    transform: translateY(0);
  }

  &:disabled {
    opacity: 0.7;
    cursor: not-allowed;
    transform: none !important;
  }

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
    transition: left 0.6s;
  }

  &:hover:not(:disabled)::before {
    left: 100%;
  }
`;

const StatusMessage = styled.div`
  margin-top: 16px;
  padding: 12px 20px;
  border-radius: 8px;
  font-weight: 500;
  background: ${props => {
    if (props.type === 'error') return '#ffebee';
    if (props.type === 'warning') return '#fff8e1';
    return '#e3f2fd';
  }};
  color: ${props => {
    if (props.type === 'error') return '#c62828';
    if (props.type === 'warning') return '#ef6c00';
    return '#1565c0';
  }};
  border: 1px solid ${props => {
    if (props.type === 'error') return '#f44336';
    if (props.type === 'warning') return '#ff9800';
    return '#2196f3';
  }};
`;

const StartScreen = ({ onStart, isLoading, isBackendHealthy }) => {
  const getStatusMessage = () => {
    if (isBackendHealthy === false) {
      return {
        type: 'error',
        message: '⚠️ Backend service is not available. Please ensure the server is running.'
      };
    }
    if (isBackendHealthy === null) {
      return {
        type: 'warning',
        message: '🔄 Checking backend connection...'
      };
    }
    return {
      type: 'success',
      message: '✅ System ready. Click below to start your FNOL process.'
    };
  };

  const statusMessage = getStatusMessage();

  // Microphone device selection logic
  const [availableDevices, setAvailableDevices] = useState([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('preferredMicDeviceId') || '';
    }
    return '';
  });

  useEffect(() => {
    const fetchDevices = async () => {
      try {
        const devices = await navigator.mediaDevices.enumerateDevices();
        const audioInputs = devices.filter(d => d.kind === 'audioinput');
        setAvailableDevices(audioInputs);

        if (!selectedDeviceId && audioInputs.length > 0) {
          setSelectedDeviceId(audioInputs[0].deviceId);
        }
      } catch (err) {
        console.error('Error fetching audio devices:', err);
      }
    };

    fetchDevices();
  }, [selectedDeviceId]);

  const handleDeviceChange = (e) => {
    const deviceId = e.target.value;
    setSelectedDeviceId(deviceId);
    if (typeof window !== 'undefined') {
      localStorage.setItem('preferredMicDeviceId', deviceId);
    }
  };

  return (
    <StartContainer>
      <WelcomeCard>
        <WelcomeIcon>
          <FaRobot />
        </WelcomeIcon>
        
        <WelcomeTitle>🎤 Voice-First FNOL Processing</WelcomeTitle>
        
        <WelcomeDescription>
          Welcome to IntactBot! I'm here to help you process your First Notice of Loss claim 
          using advanced voice recognition and AI assistance. The system will automatically 
          begin recording your voice after each response to create a seamless conversation experience.
        </WelcomeDescription>

        <FeaturesList>
          <FeatureItem>
            <FeatureIcon color="#28a745">
              <FaMicrophone />
            </FeatureIcon>
            <FeatureTitle>Smart Voice Recording</FeatureTitle>
            <FeatureDescription>
              Auto-start recording after AI responses with visual feedback and controls
            </FeatureDescription>
          </FeatureItem>

          <FeatureItem>
            <FeatureIcon color="#007bff">
              <FaComments />
            </FeatureIcon>
            <FeatureTitle>Real-time Processing</FeatureTitle>
            <FeatureDescription>
              Live claim data extraction and updates as you speak
            </FeatureDescription>
          </FeatureItem>

          <FeatureItem>
            <FeatureIcon color="#dc3545">
              <FaRobot />
            </FeatureIcon>
            <FeatureTitle>AI-Powered Agent</FeatureTitle>
            <FeatureDescription>
              Intelligent conversation flow for complete claim documentation
            </FeatureDescription>
          </FeatureItem>

          {/* New fourth informational box */}
          <FeatureItem>
            <FeatureIcon color="#6f42c1">
              <FaCode />
            </FeatureIcon>
            <FeatureTitle>JSON Repair</FeatureTitle>
            <FeatureDescription>
              Inexpensive, Targeted Edits on JSON Payload Build using TrustCall API
            </FeatureDescription>
          </FeatureItem>
        </FeaturesList>

        {isLoading ? (
          <LoadingSpinner message="Initializing FNOL process..." />
        ) : (
          <>
            {/* Microphone configuration */}
            <MicConfigContainer>
              <MicLabel htmlFor="micSelect">Select Microphone</MicLabel>
              <DeviceSelect
                id="micSelect"
                value={selectedDeviceId}
                onChange={handleDeviceChange}
              >
                {availableDevices.length === 0 && (
                  <option value="">No microphone devices found</option>
                )}
                {availableDevices.map((device, idx) => (
                  <option key={device.deviceId} value={device.deviceId}>
                    {device.label || `Microphone ${idx + 1}`}
                  </option>
                ))}
              </DeviceSelect>
            </MicConfigContainer>

            <StartButton
              onClick={onStart}
              disabled={isBackendHealthy !== true}
            >
              Start FNOL
            </StartButton>
            
            <StatusMessage type={statusMessage.type}>
              {statusMessage.message}
            </StatusMessage>
          </>
        )}
      </WelcomeCard>
    </StartContainer>
  );
};

export default StartScreen; 