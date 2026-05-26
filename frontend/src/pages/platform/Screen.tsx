import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CloseOutlined } from '@ant-design/icons';
import { Table, Progress, Tag } from 'antd';
import client from '../../api/client';

export default function PlatformScreen() {
  const navigate = useNavigate();
  const [data, setData] = useState<any>({});

  useEffect(() => {
    const fetchData = () => client.get('/platform/dashboard').then((r) => setData(r.data.data || {})).catch(() => {});
    fetchData();
    const timer = setInterval(fetchData, 30000);
    return () => clearInterval(timer);
  }, []);

  const stats = [
    ['学校总数', data.school_total || 0],
    ['学生总数', data.student_total || 0],
    ['教师总数', data.teacher_total || 0],
    ['问卷任务', data.task_total || 0],
    ['答卷总数', data.answer_sheet_total || 0],
    ['风险提示', data.risk_alert_total || 0],
    ['待处理提示', data.pending_risk_total || 0],
    ['AI 调用', data.ai_call_total || 0],
    ['短信发送', data.sms_send_total || 0],
  ];

  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 9999, background: '#061625', color: '#e6f4ff', padding: 24, overflow: 'auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <div style={{ fontSize: 26, fontWeight: 700 }}>青少年风险防范测评平台大屏</div>
          <div style={{ color: '#91caff', marginTop: 4 }}>全平台学校使用情况、完成情况与风险提示概览</div>
        </div>
        <CloseOutlined onClick={() => navigate('/platform/dashboard')} style={{ fontSize: 20, cursor: 'pointer' }} />
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(9, minmax(110px, 1fr))', gap: 12, marginBottom: 24 }}>
        {stats.map(([label, value]) => (
          <div key={label} style={{ border: '1px solid rgba(145,202,255,.24)', background: 'rgba(22,119,255,.08)', padding: 16 }}>
            <div style={{ color: '#91caff', fontSize: 13 }}>{label}</div>
            <div style={{ fontSize: 28, fontWeight: 700, marginTop: 8 }}>{value}</div>
          </div>
        ))}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <div style={{ background: 'rgba(255,255,255,.04)', padding: 16 }}>
          <h3>学校完成率排名</h3>
          <Table
            rowKey="id"
            dataSource={data.completion_rankings || []}
            pagination={false}
            size="small"
            columns={[
              { title: '学校', dataIndex: 'name' },
              { title: '完成率', dataIndex: 'completion_rate', render: (v: number) => <Progress percent={v || 0} size="small" /> },
              { title: '已填/应填', render: (_: any, r: any) => `${r.completed_count || 0}/${r.expected_count || 0}` },
            ]}
          />
        </div>
        <div style={{ background: 'rgba(255,255,255,.04)', padding: 16 }}>
          <h3>风险提示数量排名</h3>
          <Table
            rowKey="id"
            dataSource={data.risk_rankings || []}
            pagination={false}
            size="small"
            columns={[
              { title: '学校', dataIndex: 'name' },
              { title: '风险提示', dataIndex: 'risk_count', render: (v: number) => <Tag color={v > 0 ? 'orange' : 'default'}>{v || 0}</Tag> },
              { title: '待处理', dataIndex: 'pending_risk_count', render: (v: number) => <Tag color={v > 0 ? 'red' : 'default'}>{v || 0}</Tag> },
            ]}
          />
        </div>
      </div>
    </div>
  );
}
