import { useState, useEffect, useCallback, useRef } from 'react';
import { Modal, Button, Typography, Spin, Tag, Space } from 'antd';
import { RobotOutlined, CloseOutlined, ReloadOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { analyzeData } from '../../api/ai';

interface Props {
  open: boolean;
  type: 'student_risk' | 'class_report' | 'overall_report' | 'quality_report';
  data: Record<string, any>;
  title?: string;
  onClose: () => void;
}

/** 简单的 Markdown 渲染器 */
function MarkdownRenderer({ text }: { text: string }) {
  if (!text) return null;

  const lines = text.split('\n');
  const elements: React.ReactNode[] = [];
  let inList = false;

  lines.forEach((line, i) => {
    const trimmed = line.trim();

    // 空行
    if (trimmed === '') {
      inList = false;
      elements.push(<div key={i} style={{ height: 8 }} />);
      return;
    }

    // 标题
    if (trimmed.startsWith('### ')) {
      inList = false;
      elements.push(
        <h4 key={i} style={{ color: '#b7e4ff', margin: '18px 0 8px', fontSize: 15, fontWeight: 600 }}>
          {trimmed.slice(4)}
        </h4>
      );
      return;
    }
    if (trimmed.startsWith('## ')) {
      inList = false;
      elements.push(
        <h3 key={i} style={{ color: '#00d4ff', margin: '22px 0 10px', fontSize: 17, fontWeight: 700, borderBottom: '1px solid rgba(0,212,255,0.2)', paddingBottom: 6 }}>
          {trimmed.slice(3)}
        </h3>
      );
      return;
    }
    if (trimmed.startsWith('# ')) {
      inList = false;
      elements.push(
        <h2 key={i} style={{ color: '#00d4ff', margin: '24px 0 12px', fontSize: 19, fontWeight: 700 }}>
          {trimmed.slice(2)}
        </h2>
      );
      return;
    }

    // 水平分割线
    if (trimmed === '---' || trimmed === '***' || trimmed === '___') {
      inList = false;
      elements.push(<hr key={i} style={{ border: 'none', borderTop: '1px solid rgba(0,212,255,0.15)', margin: '16px 0' }} />);
      return;
    }

    // 无序列表
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      elements.push(
        <div key={i} style={{ display: 'flex', alignItems: 'flex-start', marginBottom: 4, paddingLeft: 8 }}>
          <span style={{ color: '#00d4ff', marginRight: 8, flexShrink: 0, marginTop: 1 }}>•</span>
          <span style={{ color: '#aac8e8', lineHeight: 1.9 }}>
            {renderInlineMarkdown(trimmed.slice(2))}
          </span>
        </div>
      );
      inList = true;
      return;
    }

    // 有序列表
    const olMatch = trimmed.match(/^(\d+)\.\s(.+)/);
    if (olMatch) {
      elements.push(
        <div key={i} style={{ display: 'flex', alignItems: 'flex-start', marginBottom: 4, paddingLeft: 8 }}>
          <span style={{ color: '#00d4ff', marginRight: 8, flexShrink: 0, minWidth: 20, marginTop: 1 }}>{olMatch[1]}.</span>
          <span style={{ color: '#aac8e8', lineHeight: 1.9 }}>
            {renderInlineMarkdown(olMatch[2])}
          </span>
        </div>
      );
      inList = true;
      return;
    }

    // 普通段落
    inList = false;
    elements.push(
      <p key={i} style={{ color: '#aac8e8', lineHeight: 1.9, margin: '4px 0' }}>
        {renderInlineMarkdown(trimmed)}
      </p>
    );
  });

  return <>{elements}</>;
}

/** 处理行内的加粗标记 */
function renderInlineMarkdown(text: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i} style={{ color: '#ffd666' }}>{part.slice(2, -2)}</strong>;
    }
    return <span key={i}>{part}</span>;
  });
}

/** 加载动画 */
function LoadingDots() {
  const [dots, setDots] = useState(0);
  useEffect(() => {
    const timer = setInterval(() => setDots(d => (d + 1) % 4), 500);
    return () => clearInterval(timer);
  }, []);
  return <span>{'.'.repeat(dots)}</span>;
}

export default function AiAnalysisModal({ open, type, data, title, onClose }: Props) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState('');
  const [model, setModel] = useState('');
  const [configured, setConfigured] = useState(true);
  const [error, setError] = useState('');

  const dataRef = useRef(data);
  dataRef.current = data;

  const runAnalysis = useCallback(() => {
    if (!type || !dataRef.current) return;
    setLoading(true);
    setResult('');
    setError('');
    setModel('');
    analyzeData(type, dataRef.current)
      .then((res) => {
        setResult(res.analysis);
        setModel(res.model);
        setConfigured(res.configured);
      })
      .catch((err) => {
        setError(err?.response?.data?.detail || 'AI分析请求失败，请稍后重试');
      })
      .finally(() => setLoading(false));
  }, [type]);

  useEffect(() => {
    if (open) {
      runAnalysis();
    }
  }, [open, runAnalysis]);

  const typeLabels: Record<string, string> = {
    student_risk: '学生风险分析',
    class_report: '班级报告分析',
    overall_report: '整体报告分析',
    quality_report: '答题质量分析',
  };

  return (
    <Modal
      title={null}
      open={open}
      onCancel={onClose}
      footer={null}
      width={780}
      destroyOnClose
      styles={{
        body: { padding: 0, maxHeight: '75vh', overflow: 'auto' },
        content: { padding: 0, borderRadius: 14, overflow: 'hidden' },
      }}
      closable={false}
    >
      {/* 顶部深色标题栏 */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '16px 24px',
          background: 'linear-gradient(135deg, #0a1628 0%, #132744 50%, #0d1f3c 100%)',
          borderBottom: '1px solid rgba(0,212,255,0.15)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 10,
              background: 'linear-gradient(135deg, rgba(0,212,255,0.3), rgba(0,212,255,0.1))',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: '1px solid rgba(0,212,255,0.3)',
            }}
          >
            <RobotOutlined style={{ color: '#00d4ff', fontSize: 20 }} />
          </div>
          <div>
            <div style={{ color: '#e8f4ff', fontSize: 16, fontWeight: 700, letterSpacing: 1 }}>
              {title || typeLabels[type] || 'AI 智能分析'}
            </div>
            <div style={{ color: 'rgba(168,200,232,0.6)', fontSize: 12, marginTop: 2 }}>
              {configured && model ? `模型：${model}` : 'AI智能分析系统'}
            </div>
          </div>
        </div>
        <Space size={8}>
          {result && configured && (
            <Button
              size="small"
              icon={<ReloadOutlined />}
              onClick={runAnalysis}
              style={{ color: '#8899bb', border: '1px solid rgba(136,153,187,0.3)', background: 'transparent' }}
              type="default"
            >
              重新分析
            </Button>
          )}
          <Button
            size="small"
            icon={<CloseOutlined />}
            onClick={onClose}
            style={{ color: '#8899bb', border: '1px solid rgba(136,153,187,0.3)', background: 'transparent' }}
            type="default"
          />
        </Space>
      </div>

      {/* 内容区 */}
      <div
        style={{
          padding: '24px 28px',
          background: 'linear-gradient(180deg, #0d1a2d 0%, #0f1f35 100%)',
          minHeight: 320,
        }}
      >
        {/* 加载状态 */}
        {loading && (
          <div style={{ textAlign: 'center', padding: '60px 20px' }}>
            <div style={{ position: 'relative', display: 'inline-block', marginBottom: 24 }}>
              <Spin size="large" />
              <div
                style={{
                  position: 'absolute',
                  top: '50%',
                  left: '50%',
                  transform: 'translate(-50%, -50%)',
                  color: '#00d4ff',
                  fontSize: 18,
                }}
              >
                <ThunderboltOutlined />
              </div>
            </div>
            <div style={{ color: '#00d4ff', fontSize: 16, fontWeight: 600, marginBottom: 8 }}>
              <RobotOutlined style={{ marginRight: 8 }} />
              AI 正在分析数据<LoadingDots />
            </div>
            <div style={{ color: 'rgba(168,200,232,0.5)', fontSize: 13 }}>
              正在调用AI模型进行智能分析，请稍候...
            </div>
            {/* 模拟数据处理流动画 */}
            <div style={{ marginTop: 24, display: 'flex', justifyContent: 'center', gap: 6 }}>
              {[0, 1, 2, 3, 4].map((i) => (
                <div
                  key={i}
                  style={{
                    width: 6,
                    height: 6,
                    borderRadius: 3,
                    background: '#00d4ff',
                    animation: `pulse 1.2s ease-in-out ${i * 0.2}s infinite`,
                    opacity: 0.3,
                  }}
                />
              ))}
            </div>
          </div>
        )}

        {/* 错误状态 */}
        {!loading && error && (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <div
              style={{
                width: 56,
                height: 56,
                borderRadius: '50%',
                background: 'rgba(255,77,79,0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 16px',
              }}
            >
              <CloseOutlined style={{ color: '#ff4d4f', fontSize: 24 }} />
            </div>
            <Typography.Text style={{ color: '#ff4d4f', fontSize: 14, display: 'block', marginBottom: 20 }}>
              {error}
            </Typography.Text>
            <Button onClick={runAnalysis} type="primary" icon={<ReloadOutlined />} ghost>
              重试
            </Button>
          </div>
        )}

        {/* 未配置提示 */}
        {!loading && !error && !configured && result && (
          <div style={{ padding: '10px 0' }}>
            <MarkdownRenderer text={result} />
          </div>
        )}

        {/* 分析结果 */}
        {!loading && !error && configured && result && (
          <div>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                marginBottom: 20,
                padding: '8px 14px',
                background: 'rgba(82,196,26,0.08)',
                borderRadius: 8,
                border: '1px solid rgba(82,196,26,0.2)',
              }}
            >
              <div
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: 4,
                  background: '#52c41a',
                  boxShadow: '0 0 6px rgba(82,196,26,0.5)',
                }}
              />
              <span style={{ color: '#52c41a', fontSize: 13, fontWeight: 500 }}>
                AI分析完成
              </span>
              {model && (
                <Tag color="cyan" style={{ marginLeft: 'auto', fontSize: 11, lineHeight: '20px' }}>
                  {model}
                </Tag>
              )}
            </div>
            <div style={{ lineHeight: 1.8 }}>
              <MarkdownRenderer text={result} />
            </div>
          </div>
        )}

        {/* 空状态（初次打开时不应该出现，但做兜底） */}
        {!loading && !error && !result && (
          <div style={{ textAlign: 'center', padding: 60, color: 'rgba(168,200,232,0.5)' }}>
            暂无分析数据
          </div>
        )}
      </div>
    </Modal>
  );
}
