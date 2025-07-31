import React, { useState, memo, useMemo, useCallback } from 'react';
import styled from 'styled-components';
import { FaCheckCircle, FaClock, FaExpand, FaCompress, FaCopy } from 'react-icons/fa';
import { toast } from 'react-toastify';

const PayloadContainer = styled.div`
  background: white;
  border-radius: 16px;
  border: 2px solid #e0e0e0;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  height: fit-content;
  max-height: 140vh;
  width: 125%;
  
  @media (max-width: 1200px) {
    max-height: 700px;
    width: 125%;
  }
`;

const PayloadHeader = styled.div`
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  padding: 16px 20px;
  border-bottom: 2px solid #e0e0e0;
  display: flex;
  justify-content: space-between;
  align-items: center;
`;

const PayloadTitle = styled.h3`
  margin: 0;
  color: #2c3e50;
  font-size: 18px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 12px;
`;

const StatusBadge = styled.span`
  background: ${props => props.$isComplete ? '#28a745' : '#ffc107'};
  color: ${props => props.$isComplete ? 'white' : '#000'};
  font-size: 12px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  display: flex;
  align-items: center;
  gap: 4px;
`;

const ExpandButton = styled.button`
  background: none;
  border: none;
  color: #666;
  font-size: 16px;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: all 0.3s ease;

  &:hover {
    background: #e9ecef;
    color: #333;
  }
`;

const PayloadContent = styled.div`
  height: ${props => props.$expanded ? 'auto' : '700px'};
  overflow-y: auto;
  transition: height 0.3s ease;
`;

const CodeContainer = styled.div`
  position: relative;
  background: #1e1e1e;
  border-radius: 8px;
  margin: 0;
  overflow: hidden;
`;

const CodeHeader = styled.div`
  background: #2d2d30;
  color: #cccccc;
  padding: 8px 16px;
  font-size: 12px;
  font-weight: 500;
  border-bottom: 1px solid #3e3e42;
  display: flex;
  justify-content: space-between;
  align-items: center;
`;

const CopyButton = styled.button`
  background: none;
  border: none;
  color: #cccccc;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
  transition: all 0.2s ease;

  &:hover {
    background: #3e3e42;
    color: #ffffff;
  }
`;

const CodeBlock = styled.pre`
  margin: 0;
  padding: 16px;
  background: #1e1e1e;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.4;
  color: #d4d4d4;
  white-space: pre-wrap;
  word-wrap: break-word;
  overflow-x: auto;
  max-height: 625px;
  overflow-y: auto;

  /* JSON Syntax Highlighting */
  .json-key {
    color: #9cdcfe;
    font-weight: normal;
  }
  
  .json-string {
    color: #ce9178;
  }
  
  .json-number {
    color: #b5cea8;
  }
  
  .json-boolean {
    color: #569cd6;
  }
  
  .json-null {
    color: #569cd6;
  }
  
  .json-punctuation {
    color: #d4d4d4;
  }
`;

const InfoPanel = styled.div`
  padding: 16px 20px;
  background: #f8f9fa;
  border-top: 1px solid #e0e0e0;
  font-size: 13px;
  color: #666;
  line-height: 1.5;
`;

const EmptyState = styled.div`
  padding: 40px 20px;
  text-align: center;
  color: #999;
  font-style: italic;
`;

const LoadingState = styled.div`
  padding: 40px 20px;
  text-align: center;
  color: #666;
  
  &::before {
    content: '⏳';
    font-size: 24px;
    display: block;
    margin-bottom: 12px;
  }
`;

// Optimized JSON highlighting with memoization
const highlightJson = (jsonString) => {
  if (!jsonString) return '';
  
  return jsonString
    .replace(/"([^"]+)"(\s*:)/g, '<span class="json-key">"$1"</span>$2')
    .replace(/:\s*"([^"]*)"/g, ': <span class="json-string">"$1"</span>')
    .replace(/:\s*(\d+(?:\.\d+)?)/g, ': <span class="json-number">$1</span>')
    .replace(/:\s*(true|false)/g, ': <span class="json-boolean">$1</span>')
    .replace(/:\s*(null)/g, ': <span class="json-null">$1</span>')
    .replace(/([{}[\],])/g, '<span class="json-punctuation">$1</span>');
};

const PayloadDisplay = memo(({ payload = {}, isFormComplete = false }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  // Memoize payload formatting to avoid re-parsing on every render
  const formattedPayload = useMemo(() => {
    try {
      if (!payload || Object.keys(payload).length === 0) {
        return null;
      }
      return JSON.stringify(payload, null, 2);
    } catch (error) {
      return `Error formatting payload: ${error.message}`;
    }
  }, [payload]);

  // Memoize highlighted JSON to avoid re-highlighting on every render
  const highlightedJson = useMemo(() => {
    if (!formattedPayload || formattedPayload.startsWith('Error')) {
      return formattedPayload;
    }
    return highlightJson(formattedPayload);
  }, [formattedPayload]);

  // Optimize expand/collapse toggle
  const toggleExpanded = useCallback(() => {
    setIsExpanded(prev => !prev);
  }, []);

  // Optimize copy functionality
  const handleCopyJson = useCallback(() => {
    if (!formattedPayload) {
      toast.error('No data to copy');
      return;
    }
    
    try {
      navigator.clipboard.writeText(formattedPayload);
      toast.success('JSON copied to clipboard!');
    } catch (error) {
      // Fallback for older browsers
      try {
        const textArea = document.createElement('textarea');
        textArea.value = formattedPayload;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        toast.success('JSON copied to clipboard!');
      } catch (fallbackError) {
        toast.error('Failed to copy JSON');
      }
    }
  }, [formattedPayload]);

  // Memoize status badge content
  const statusBadgeContent = useMemo(() => {
    return isFormComplete ? (
      <>
        <FaCheckCircle />
        Complete
      </>
    ) : (
      <>
        <FaClock />
        In Progress
      </>
    );
  }, [isFormComplete]);

  // Memoize info panel content
  const infoPanelContent = useMemo(() => (
    <>
      <strong>Real-time Payload:</strong> This panel displays the current state of claim data 
      being processed by the agent. Updates automatically as the conversation progresses.
      TrustCall patches are applied incrementally to maintain data consistency.
      {isFormComplete && (
        <>
          <br />
          <strong style={{ color: '#28a745' }}>✅ Form Complete:</strong> All required claim 
          information has been collected successfully.
        </>
      )}
    </>
  ), [isFormComplete]);

  return (
    <PayloadContainer>
      <PayloadHeader>
        <PayloadTitle>
          📋 Claim Payload
                  <StatusBadge $isComplete={isFormComplete}>
          {statusBadgeContent}
        </StatusBadge>
        </PayloadTitle>
        
        <ExpandButton onClick={toggleExpanded}>
          {isExpanded ? <FaCompress /> : <FaExpand />}
        </ExpandButton>
      </PayloadHeader>

      <PayloadContent $expanded={isExpanded}>
        {!formattedPayload ? (
          <EmptyState>
            No payload data available yet.<br />
            Start the conversation to see claim data appear here.
          </EmptyState>
        ) : formattedPayload.startsWith('Error') ? (
          <LoadingState>
            {formattedPayload}
          </LoadingState>
        ) : (
          <CodeContainer>
            <CodeHeader>
              <span>📄 JSON Payload</span>
              <CopyButton onClick={handleCopyJson}>
                <FaCopy />
                Copy
              </CopyButton>
            </CodeHeader>
            <CodeBlock 
              dangerouslySetInnerHTML={{ 
                __html: highlightedJson 
              }}
            />
          </CodeContainer>
        )}
      </PayloadContent>

      <InfoPanel>
        {infoPanelContent}
      </InfoPanel>
    </PayloadContainer>
  );
});

PayloadDisplay.displayName = 'PayloadDisplay';

export default PayloadDisplay; 