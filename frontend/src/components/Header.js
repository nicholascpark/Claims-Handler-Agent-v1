import React from 'react';
import styled from 'styled-components';

const HeaderContainer = styled.header`
  background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
  border-bottom: 2px solid #e0e0e0;
  padding: 16px 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
`;

const HeaderContent = styled.div`
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  position: relative;
`;

const LogoSection = styled.div`
  position: absolute;
  right: 0;
  display: flex;
  align-items: center;
  gap: 12px;
`;

const LogoImage = styled.img`
  max-width: 100px;
  height: auto;
  object-fit: contain;
  transition: transform 0.3s ease;
  
  &:hover {
    transform: scale(1.05);
  }
`;

const LogoText = styled.div`
  h1 {
    font-size: 20px;
    font-weight: 600;
    color: #2c3e50;
    margin: 0;
    letter-spacing: -0.5px;
  }
  
  p {
    font-size: 12px;
    color: #666;
    margin: 0;
    font-weight: 500;
  }
`;

const CenterContent = styled.div`
  width: 100%;
  text-align: center;
`;

const MainTitle = styled.h1`
  font-size: 32px;
  font-weight: 700;
  color: #2c3e50;
  margin: 0 0 4px 0;
  letter-spacing: -1px;
`;

const Subtitle = styled.p`
  font-size: 16px;
  color: #666;
  margin: 0;
  font-weight: 500;
`;

const Header = () => {
  return (
    <HeaderContainer>
      <HeaderContent>
        <CenterContent>
          <MainTitle>IntactBot-FNOL-v1.0</MainTitle>
          <Subtitle>First Notice of Loss Processing Agent</Subtitle>
        </CenterContent>
        
        <LogoSection>
          <LogoText>
            <h1>IntactBot</h1>
            <p>FNOL v1.0</p>
          </LogoText>
          <LogoImage 
            src="/intactbot_logo.png" 
            alt="IntactBot Logo"
            onError={(e) => {
              // Fallback if logo doesn't load
              e.target.style.display = 'none';
            }}
          />
        </LogoSection>
      </HeaderContent>
    </HeaderContainer>
  );
};

export default Header; 