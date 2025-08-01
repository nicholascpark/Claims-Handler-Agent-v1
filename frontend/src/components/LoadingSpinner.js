import React from 'react';
import styled, { keyframes } from 'styled-components';
import { FaSpinner } from 'react-icons/fa';

const spinAnimation = keyframes`
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
`;

const LoadingContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
  gap: 16px;
`;

const SpinnerIcon = styled(FaSpinner)`
  font-size: 32px;
  color: #dc3545;
  animation: ${spinAnimation} 1s linear infinite;
`;

const LoadingText = styled.p`
  color: #666;
  font-size: 16px;
  font-weight: 500;
  margin: 0;
  text-align: center;
`;

const LoadingSpinner = ({ message = "Loading..." }) => {
  return (
    <LoadingContainer>
      <SpinnerIcon />
      <LoadingText>{message}</LoadingText>
    </LoadingContainer>
  );
};

export default LoadingSpinner; 