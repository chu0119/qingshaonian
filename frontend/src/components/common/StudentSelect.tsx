import { useState, useCallback, useEffect, useRef } from 'react';
import { Select, Space, Spin, Typography } from 'antd';
import { UserOutlined } from '@ant-design/icons';
import client from '../../api/client';

interface StudentOption {
  value: number;
  label: React.ReactNode;
}

interface Props {
  value?: number;
  onChange?: (value: number) => void;
  placeholder?: string;
  style?: React.CSSProperties;
}

function toStudentOption(s: any): StudentOption {
  return {
    value: s.id,
    label: (
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Space>
          <UserOutlined />
          <span style={{ fontWeight: 500 }}>{s.real_name}</span>
          <span style={{ color: '#888', fontSize: 12 }}>{s.student_no}</span>
        </Space>
        <span style={{ color: '#4A90D9', fontSize: 12 }}>{s.grade_name} {s.class_name}</span>
      </div>
    ),
  };
}

export default function StudentSelect({ value, onChange, placeholder, style }: Props) {
  const [options, setOptions] = useState<StudentOption[]>([]);
  const [searching, setSearching] = useState(false);
  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!value) return;
    let cancelled = false;
    client.get(`/users/students/${value}`)
      .then(res => {
        if (!cancelled) {
          setOptions(prev => prev.some(item => item.value === value) ? prev : [toStudentOption(res.data.data), ...prev]);
        }
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [value]);

  const handleSearch = useCallback((keyword: string) => {
    if (!keyword || keyword.length < 1) { setOptions([]); return; }
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    searchTimerRef.current = setTimeout(async () => {
      setSearching(true);
      try {
        const res = await client.get('/users/students', { params: { keyword, page_size: 20 } });
        const students = res.data.data?.items || [];
        setOptions(students.map(toStudentOption));
      } catch { setOptions([]); }
      finally { setSearching(false); }
    }, 300);
  }, []);

  return (
    <Select
      showSearch
      value={value}
      onChange={onChange}
      placeholder={placeholder || '输入姓名或学号搜索学生'}
      style={style}
      filterOption={false}
      onSearch={handleSearch}
      notFoundContent={searching ? <Spin size="small" /> : <Typography.Text type="secondary">输入关键词搜索</Typography.Text>}
      options={options}
      allowClear
      size="large"
    />
  );
}
