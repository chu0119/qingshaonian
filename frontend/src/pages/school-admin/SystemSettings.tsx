import { useState, useEffect, useCallback } from 'react';
import {
  Card, Form, Input, Button, message, Modal, Popconfirm, Table,
  InputNumber, Typography, Tag, Space, Tabs, Descriptions, Divider, Alert, Empty,
  Select, Switch,
} from 'antd';
import {
  PlusOutlined, DeleteOutlined, SafetyOutlined, InfoCircleOutlined,
  SettingOutlined, LockOutlined,
  BankOutlined, WarningOutlined, DesktopOutlined, RobotOutlined,
  ApiOutlined, KeyOutlined, CheckCircleOutlined, ReloadOutlined,
} from '@ant-design/icons';
import {
  getSchoolInfo, updateSchoolInfo, getRiskConfig, updateRiskConfig,
  getAdminGrades, addGrade, deleteGrade,
  getSmsConfig, updateSmsConfig, getScreenConfig, updateScreenConfig,
  type SchoolInfo, type RiskLevelItem, type GradeItem, type SmsConfig, type ScreenConfig,
} from '../../api/system';
import { getAiConfig, updateAiConfig, type AiConfig } from '../../api/ai';

const { Title, Text, Paragraph } = Typography;

// 预置国产AI服务商
const AI_PROVIDERS: Record<string, { name: string; url: string }> = {
  deepseek: { name: 'DeepSeek（深度求索）', url: 'https://api.deepseek.com' },
  qwen: { name: '通义千问（阿里云）', url: 'https://dashscope.aliyuncs.com/compatible-mode' },
  zhipu: { name: '智谱AI（GLM）', url: 'https://open.bigmodel.cn/api/paas/v4' },
  moonshot: { name: '月之暗面（Kimi）', url: 'https://api.moonshot.cn' },
  lingyi: { name: '零一万物（Yi）', url: 'https://api.lingyiwanwu.com' },
  baichuan: { name: '百川智能', url: 'https://api.baichuan-ai.com' },
  openai: { name: 'OpenAI', url: 'https://api.openai.com' },
  custom: { name: '自定义', url: '' },
};

// 预置国内主流短信服务商
const SMS_PROVIDERS: Record<string, { name: string; url: string }> = {
  tencent: { name: '腾讯云短信', url: 'https://sms.tencentcloudapi.com' },
  aliyun: { name: '阿里云短信', url: 'https://dysmsapi.aliyuncs.com' },
  custom: { name: '自定义', url: '' },
};

export default function SystemSettings() {
  const [activeTab, setActiveTab] = useState('basic');

  // ---- school info state ----
  const [schoolInfo, setSchoolInfo] = useState<SchoolInfo | null>(null);
  const [schoolLoading, setSchoolLoading] = useState(false);
  const [savingSchool, setSavingSchool] = useState(false);
  const [schoolForm] = Form.useForm();

  // ---- SMS config state ----
  const [smsConfig, setSmsConfig] = useState<SmsConfig | null>(null);
  const [smsLoading, setSmsLoading] = useState(false);
  const [selectedSmsProvider, setSelectedSmsProvider] = useState<string>('tencent');
  const [savingSms, setSavingSms] = useState(false);
  const [smsForm] = Form.useForm();

  // ---- risk config state ----
  const [riskLevels, setRiskLevels] = useState<RiskLevelItem[]>([]);
  const [riskLoading, setRiskLoading] = useState(false);
  const [savingRisk, setSavingRisk] = useState(false);
  const [riskForm] = Form.useForm();

  // ---- grade state ----
  const [grades, setGrades] = useState<GradeItem[]>([]);
  const [gradesLoading, setGradesLoading] = useState(false);
  const [gradeModalOpen, setGradeModalOpen] = useState(false);
  const [addingGrade, setAddingGrade] = useState(false);
  const [gradeForm] = Form.useForm();

  // ---- screen config state ----
  const [screenConfig, setScreenConfig] = useState<ScreenConfig | null>(null);
  const [screenLoading, setScreenLoading] = useState(false);
  const [savingScreen, setSavingScreen] = useState(false);

  // ---- AI config state ----
  const [aiConfig, setAiConfig] = useState<AiConfig | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [savingAi, setSavingAi] = useState(false);
  const [testingAi, setTestingAi] = useState(false);
  const [aiForm] = Form.useForm();
  const [selectedProvider, setSelectedProvider] = useState<string>('deepseek');
  const [modelList, setModelList] = useState<{ id: string; owned_by?: string }[]>([]);
  const [fetchingModels, setFetchingModels] = useState(false);

  // 获取模型列表
  const handleFetchModels = async () => {
    const apiUrl = aiForm.getFieldValue('api_url');
    const apiKey = aiForm.getFieldValue('api_key');
    if (!apiUrl || !apiKey) {
      message.warning('请先填写接口地址和API密钥');
      return;
    }
    setFetchingModels(true);
    try {
      // 调用 /v1/models 端点
      const base = apiUrl.replace(/\/chat\/completions\/?$/, '').replace(/\/v1\/?$/, '');
      const resp = await fetch(`${base}/v1/models`, {
        headers: { 'Authorization': `Bearer ${apiKey}` },
      });
      if (!resp.ok) {
        const errText = await resp.text();
        message.error(`获取模型失败: ${resp.status} ${errText.substring(0, 100)}`);
        return;
      }
      const data = await resp.json();
      const models = (data.data || []).map((m: any) => ({ id: m.id, owned_by: m.owned_by || '' }));
      setModelList(models);
      message.success(`获取到 ${models.length} 个模型`);
      // 如果有模型且当前未选择，自动选第一个
      if (models.length > 0 && !aiForm.getFieldValue('model_name')) {
        const defaultModel = models.find((m: any) => m.id.includes('chat')) || models[0];
        aiForm.setFieldsValue({ model_name: defaultModel.id });
      }
    } catch (e: any) {
      message.error(`获取模型失败: ${e.message || '网络错误'}`);
    } finally {
      setFetchingModels(false);
    }
  };

  // ==================== data fetching ====================

  const fetchSchoolInfo = useCallback(async () => {
    setSchoolLoading(true);
    try {
      const info = await getSchoolInfo();
      if (info) {
        setSchoolInfo(info);
        schoolForm.setFieldsValue({
          name: info.name,
          code: info.code,
          address: info.address,
          phone: info.phone,
        });
      }
    } catch {
      message.error('获取学校信息失败');
    } finally {
      setSchoolLoading(false);
    }
  }, [schoolForm]);

  const fetchSmsConfig = useCallback(async () => {
    setSmsLoading(true);
    try {
      const data = await getSmsConfig();
      setSmsConfig(data);
    } catch {
      // SMS配置为预留接口，获取失败不提示错误
    } finally {
      setSmsLoading(false);
    }
  }, []);

  const handleSaveSms = async () => {
    try {
      const values = await smsForm.validateFields();
      setSavingSms(true);
      await updateSmsConfig({
        sms_api_url: values.sms_api_url || '',
        sms_template_id: values.sms_template_id || '',
        // 根据平台类型发送不同的密钥字段
        ...(selectedSmsProvider === 'tencent' ? {
          sms_secret_id: values.sms_secret_id || '',
          sms_secret_key: values.sms_secret_key || '',
        } : {}),
        ...(selectedSmsProvider === 'aliyun' ? {
          sms_access_key: values.sms_access_key || '',
          sms_access_secret: values.sms_access_secret || '',
        } : {}),
        ...(selectedSmsProvider === 'custom' ? {
          sms_app_key: values.sms_app_key || '',
        } : {}),
      });
      message.success('短信配置保存成功');
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'errorFields' in err) return;
      message.error('保存失败，请重试');
    } finally {
      setSavingSms(false);
    }
  };

  const fetchRiskConfig = useCallback(async () => {
    setRiskLoading(true);
    try {
      const data = await getRiskConfig();
      if (data?.risk_levels) {
        setRiskLevels(data.risk_levels);
        const fields: Record<string, number> = {};
        data.risk_levels.forEach((r: any) => {
          fields[`${r.level}_min`] = r.min;
          fields[`${r.level}_max`] = r.max;
        });
        riskForm.setFieldsValue(fields);
      }
    } catch {
      // 风险配置为可选，静默处理
    } finally {
      setRiskLoading(false);
    }
  }, []); // riskForm 引用稳定，无需加入依赖

  const fetchGrades = useCallback(async () => {
    setGradesLoading(true);
    try {
      const list = await getAdminGrades();
      setGrades(list);
    } catch {
      message.error('获取年级列表失败');
    } finally {
      setGradesLoading(false);
    }
  }, []);

  // ==================== screen config fetch & save ====================

  const fetchScreenConfig = useCallback(async () => {
    setScreenLoading(true);
    try {
      const data = await getScreenConfig();
      setScreenConfig(data);
    } catch {
      // 数据大屏配置为可选功能，获取失败不提示错误
    } finally {
      setScreenLoading(false);
    }
  }, []);

  const handleSaveScreen = async () => {
    try {
      setSavingScreen(true);
      await updateScreenConfig({
        screen_title: screenConfig?.screen_title || '',
        screen_subtitle: screenConfig?.screen_subtitle || '',
      });
      message.success('数据大屏配置保存成功');
    } catch {
      message.error('保存失败，请重试');
    } finally {
      setSavingScreen(false);
    }
  };

  // ==================== AI config fetch & save ====================

  const fetchAiConfig = useCallback(async () => {
    setAiLoading(true);
    try {
      const data = await getAiConfig();
      setAiConfig(data);
      aiForm.setFieldsValue({
        api_url: data.api_url || '',
        api_key: data.api_key || '',
        model_name: data.model_name || 'deepseek-chat',
      });
    } catch {
      // AI配置为可选功能，获取失败不提示错误
    } finally {
      setAiLoading(false);
    }
  }, [aiForm]);

  // ===== 初始化加载（必须在所有 useCallback 之后） =====
  useEffect(() => {
    fetchSchoolInfo();
    fetchSmsConfig();
    fetchRiskConfig();
    fetchGrades();
    fetchScreenConfig();
    fetchAiConfig();
  }, [fetchSchoolInfo, fetchSmsConfig, fetchRiskConfig, fetchGrades, fetchScreenConfig, fetchAiConfig]);

  const handleSaveAiConfig = async () => {
    try {
      const values = await aiForm.validateFields();
      setSavingAi(true);
      await updateAiConfig({
        api_url: values.api_url || '',
        api_key: values.api_key || '',
        model_name: values.model_name || 'deepseek-chat',
      });
      message.success('AI配置保存成功');
      fetchAiConfig();
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'errorFields' in err) return;
      message.error('保存失败，请重试');
    } finally {
      setSavingAi(false);
    }
  };

  const handleTestConnection = async () => {
    try {
      const values = await aiForm.validateFields(['api_url', 'api_key', 'model_name']);
      setTestingAi(true);
      message.loading({ content: '正在测试AI接口连接...', key: 'test-ai', duration: 0 });

      // 先保存当前配置
      const apiKey = values.api_key;
      // 如果api_key包含***说明是脱敏后的值，需要特殊处理
      // 先用当前表单值尝试保存
      await updateAiConfig({
        api_url: values.api_url || '',
        api_key: apiKey || '',
        model_name: values.model_name || 'deepseek-chat',
      });

      // 发送一个简单的测试请求
      const res = await fetch('/api/v1/ai/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: JSON.stringify({
          type: 'quality_report',
          data: { total: 'N/A', effective_rate: 'N/A', suggest_retest_count: 'N/A', quality_level_distribution: 'N/A', anomaly_summary: 'N/A' },
        }),
      });

      const result = await res.json();
      message.destroy('test-ai');

      if (result.code === 200 && result.data?.configured) {
        message.success('AI接口连接成功！配置已生效');
        fetchAiConfig();
      } else if (result.code === 200 && !result.data?.configured) {
        message.warning('配置已保存，但未能验证连接（可能API密钥未正确保存）。请确认密钥后重试。');
      } else {
        message.error(`连接测试失败：${result.data?.analysis || result.message || '未知错误'}`);
      }
    } catch (err: unknown) {
      message.destroy('test-ai');
      if (err && typeof err === 'object' && 'errorFields' in err) return;
      message.error('连接测试失败，请检查网络和配置');
    } finally {
      setTestingAi(false);
    }
  };

  // ==================== school info save ====================

  const handleSaveSchool = async () => {
    try {
      const values = await schoolForm.validateFields();
      setSavingSchool(true);
      await updateSchoolInfo({
        name: values.name,
        address: values.address || '',
        phone: values.phone || '',
      });
      message.success('学校信息保存成功');
      fetchSchoolInfo();
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'errorFields' in err) return;
      message.error('保存失败，请重试');
    } finally {
      setSavingSchool(false);
    }
  };

  // ==================== risk config save ====================

  const handleSaveRisk = async () => {
    try {
      const values = await riskForm.validateFields();
      setSavingRisk(true);

      const updatedLevels = riskLevels.map((r) => ({
        ...r,
        min: values[`${r.level}_min`] as number,
        max: values[`${r.level}_max`] as number,
      }));

      for (const level of updatedLevels) {
        if (level.min > level.max) {
          message.error(`"${level.label}"的最低分不能大于最高分`);
          setSavingRisk(false);
          return;
        }
      }

      await updateRiskConfig({ risk_levels: updatedLevels });
      setRiskLevels(updatedLevels);
      message.success('风险等级配置保存成功');
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'errorFields' in err) return;
      message.error('保存失败，请重试');
    } finally {
      setSavingRisk(false);
    }
  };

  // ==================== grade management ====================

  const openAddGrade = () => {
    gradeForm.resetFields();
    gradeForm.setFieldsValue({ sort_order: grades.length });
    setGradeModalOpen(true);
  };

  const handleAddGrade = async () => {
    try {
      const values = await gradeForm.validateFields();
      setAddingGrade(true);
      await addGrade({ name: values.name, sort_order: values.sort_order ?? 0 });
      message.success('年级添加成功');
      setGradeModalOpen(false);
      fetchGrades();
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'errorFields' in err) return;
      message.error('添加失败，请重试');
    } finally {
      setAddingGrade(false);
    }
  };

  const handleDeleteGrade = async (id: number) => {
    try {
      await deleteGrade(id);
      message.success('删除成功');
      fetchGrades();
    } catch {
      message.error('删除失败，请重试');
    }
  };

  // ==================== table columns ====================

  const riskColumns = [
    {
      title: '风险等级',
      dataIndex: 'label',
      key: 'label',
      width: 120,
      render: (text: string, record: RiskLevelItem) => (
        <Tag color={record.color} style={{ borderRadius: 4, fontWeight: 500 }}>
          <WarningOutlined style={{ marginRight: 4 }} />
          {text}
        </Tag>
      ),
    },
    {
      title: '最低分',
      dataIndex: 'level',
      key: 'min',
      width: 150,
      render: (_: string, record: RiskLevelItem) => (
        <Form.Item
          name={`${record.level}_min`}
          noStyle
          rules={[{ required: true, message: '必填' }]}
        >
          <InputNumber min={0} max={100} style={{ width: 100 }} placeholder="0" />
        </Form.Item>
      ),
    },
    {
      title: '最高分',
      dataIndex: 'level',
      key: 'max',
      width: 150,
      render: (_: string, record: RiskLevelItem) => (
        <Form.Item
          name={`${record.level}_max`}
          noStyle
          rules={[{ required: true, message: '必填' }]}
        >
          <InputNumber min={0} max={100} style={{ width: 100 }} placeholder="100" />
        </Form.Item>
      ),
    },
    {
      title: '说明',
      key: 'desc',
      render: (_: unknown, record: RiskLevelItem) => (
        <Text type="secondary" style={{ fontSize: 13 }}>
          {record.level === 'low' && '学生心理健康状况良好'}
          {record.level === 'medium' && '建议关注并观察'}
          {record.level === 'high' && '需要心理辅导干预'}
          {record.level === 'urgent' && '需要立即介入处理'}
        </Text>
      ),
    },
  ];

  const gradeColumns = [
    { title: '年级名称', dataIndex: 'name', key: 'name', width: 200 },
    { title: '排序', dataIndex: 'sort_order', key: 'sort_order', width: 80 },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_: unknown, record: GradeItem) => (
        <Popconfirm
          title="确定删除该年级？"
          description="删除后相关班级和学生的年级信息将受到影响"
          onConfirm={() => handleDeleteGrade(record.id)}
          okText="确定"
          cancelText="取消"
        >
          <Button size="small" danger icon={<DeleteOutlined />}>
            删除
          </Button>
        </Popconfirm>
      ),
    },
  ];

  // ==================== Tab items ====================

  const tabItems = [
    {
      key: 'basic',
      label: (
        <span>
          <SettingOutlined />
          基础设置
        </span>
      ),
      children: (
        <Card loading={schoolLoading} bordered={false} style={{ boxShadow: 'none' }}>
          <Form
            form={schoolForm}
            layout="vertical"
            style={{ maxWidth: 560 }}
            disabled={savingSchool}
          >
            <Form.Item
              name="name"
              label="学校名称"
              rules={[{ required: true, message: '请输入学校名称' }]}
            >
              <Input placeholder="请输入学校名称" size="large" />
            </Form.Item>

            <Form.Item name="code" label="学校编码">
              <Input disabled placeholder="系统自动分配" />
            </Form.Item>

            <Form.Item name="address" label="学校地址">
              <Input placeholder="请输入学校地址" />
            </Form.Item>

            <Form.Item
              name="phone"
              label="联系电话"
              rules={[{ pattern: /^[\d\-+() ]*$/, message: '请输入有效的电话号码' }]}
            >
              <Input placeholder="请输入联系电话" />
            </Form.Item>

            <Divider style={{ margin: '24px 0 16px' }} />

            <Form.Item>
              <Button
                type="primary"
                loading={savingSchool}
                onClick={handleSaveSchool}
                size="large"
              >
                保存基本信息
              </Button>
            </Form.Item>
          </Form>
        </Card>
      ),
    },
    {
      key: 'security',
      label: (
        <span>
          <LockOutlined />
          安全设置
        </span>
      ),
      children: (
        <div>
          <Card title={<Space><LockOutlined style={{ color: '#1677ff' }} /><span>短信服务配置</span></Space>}
            bordered={false} style={{ boxShadow: 'none', marginBottom: 24 }}>
            <Alert message="短信服务用于重置密码验证和登录二次验证。选择短信平台后填写相应的参数即可启用。" type="info" showIcon style={{ marginBottom: 20 }} />

            <Form form={smsForm} layout="vertical" style={{ maxWidth: 600 }} disabled={savingSms}>
              {/* 平台选择 */}
              <Form.Item label="短信平台">
                <Select size="large" value={selectedSmsProvider} onChange={(v) => {
                  setSelectedSmsProvider(v);
                  const p = SMS_PROVIDERS[v];
                  if (p) {
                    smsForm.setFieldsValue({ sms_api_url: p.url, sms_sign: '青少年心理健康' });
                  }
                }} options={Object.entries(SMS_PROVIDERS).map(([k, p]) => ({ value: k, label: p.name }))} />
              </Form.Item>

              <Form.Item name="sms_api_url" label="API地址" rules={[{ required: true }]}>
                <Input placeholder="选择平台后自动填充，也可手动修改" size="large" />
              </Form.Item>

              {selectedSmsProvider === 'tencent' && (
                <>
                  <Form.Item name="sms_secret_id" label="SecretId" rules={[{ required: true }]}>
                    <Input placeholder="腾讯云 SecretId" size="large" />
                  </Form.Item>
                  <Form.Item name="sms_secret_key" label="SecretKey">
                    <Input.Password placeholder="腾讯云 SecretKey" size="large" />
                  </Form.Item>
                </>
              )}

              {selectedSmsProvider === 'aliyun' && (
                <>
                  <Form.Item name="sms_access_key" label="AccessKey ID" rules={[{ required: true }]}>
                    <Input placeholder="阿里云 AccessKey ID" size="large" />
                  </Form.Item>
                  <Form.Item name="sms_access_secret" label="AccessKey Secret">
                    <Input.Password placeholder="阿里云 AccessKey Secret" size="large" />
                  </Form.Item>
                </>
              )}

              {(selectedSmsProvider === 'custom' || !selectedSmsProvider) && (
                <Form.Item name="sms_app_key" label="API密钥" rules={[{ required: true }]}>
                  <Input.Password placeholder="第三方短信平台API密钥" size="large" />
                </Form.Item>
              )}

              <Form.Item name="sms_template_id" label="短信模板ID" rules={[{ required: true }]}>
                <Input placeholder="短信平台审核通过的模板ID" size="large" />
              </Form.Item>

              <Form.Item name="sms_sign" label="短信签名">
                <Input placeholder="短信签名内容（如：青少年心理健康）" size="large" />
              </Form.Item>

              <Divider />
              <Button type="primary" loading={savingSms} onClick={handleSaveSms} icon={<CheckCircleOutlined />} size="large">
                保存短信配置
              </Button>
            </Form>
          </Card>
        </div>
      ),
    },
    {
      key: 'ai',
      label: (
        <span>
          <RobotOutlined />
          AI分析设置
        </span>
      ),
      children: (
        <Card loading={aiLoading} bordered={false} style={{ boxShadow: 'none' }}>
          <Alert
            message="配置AI大模型接口，用于系统内各报告页面的「AI一键分析」功能。选择厂商后自动填充接口地址，填入Key即可获取模型列表。"
            type="info" showIcon style={{ marginBottom: 20, borderRadius: 8 }}
          />

          <Form form={aiForm} layout="vertical" style={{ maxWidth: 600 }} disabled={savingAi}>
            {/* 厂商选择 */}
            <Form.Item label={<Space><ApiOutlined /><span>AI服务商</span></Space>}>
              <Select
                size="large"
                placeholder="请选择AI服务商"
                value={selectedProvider}
                onChange={(v) => {
                  setSelectedProvider(v);
                  const provider = AI_PROVIDERS[v];
                  if (provider) {
                    aiForm.setFieldsValue({ api_url: provider.url });
                  }
                }}
                options={Object.entries(AI_PROVIDERS).map(([key, p]) => ({
                  value: key, label: p.name,
                }))}
              />
            </Form.Item>

            <Form.Item name="api_url" label={<Space><ApiOutlined /><span>接口地址</span></Space>}
              rules={[{ required: true, message: '请输入AI接口地址' }]}>
              <Input placeholder="选择厂商后自动填充，也可手动输入" size="large" />
            </Form.Item>

            <Form.Item name="api_key" label={<Space><KeyOutlined /><span>API密钥</span></Space>}>
              <Input.Password placeholder="请输入API密钥" size="large"
                iconRender={(visible) => (visible ? <span>隐藏</span> : <span>显示</span>)} />
            </Form.Item>

            {/* 模型获取和选择 */}
            <Form.Item name="model_name" label={<Space><RobotOutlined /><span>模型选择</span></Space>} rules={[{ required: true, message: '请选择模型' }]}>
              <div style={{ display: 'flex', gap: 8 }}>
                <Select
                  size="large" style={{ flex: 1 }}
                  placeholder="请先点击「获取模型列表」"
                  loading={fetchingModels}
                  options={modelList.map(m => ({ value: m.id, label: `${m.id}${m.owned_by ? ' (' + m.owned_by + ')' : ''}` }))}
                  showSearch
                  filterOption={(input, option) =>
                    (option?.label as string)?.toLowerCase().includes(input.toLowerCase())
                  }
                />
                <Button size="large" onClick={handleFetchModels} loading={fetchingModels}
                  icon={<ReloadOutlined />}>
                  获取模型
                </Button>
              </div>
            </Form.Item>

            {/* 配置状态 */}
            <div style={{ marginBottom: 20, padding: '10px 16px',
              background: aiConfig?.configured ? '#f6ffed' : '#fff7e6',
              borderRadius: 8, border: aiConfig?.configured ? '1px solid #b7eb8f' : '1px solid #ffd591',
              display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{ width: 8, height: 8, borderRadius: 4,
                background: aiConfig?.configured ? '#52c41a' : '#faad14',
                boxShadow: aiConfig?.configured ? '0 0 6px rgba(82,196,26,0.5)' : '0 0 6px rgba(250,173,20,0.5)' }} />
              <Text style={{ fontSize: 13, color: aiConfig?.configured ? '#52c41a' : '#faad14' }}>
                {aiConfig?.configured ? 'AI接口已配置' : 'AI接口未配置或配置不完整'}
              </Text>
            </div>

            <Divider style={{ margin: '24px 0 16px' }} />
            <Form.Item>
              <Space size={12}>
                <Button type="primary" loading={savingAi} onClick={handleSaveAiConfig}
                  size="large"
                  icon={<CheckCircleOutlined />}
                >
                  保存配置
                </Button>
                <Button
                  loading={testingAi}
                  onClick={handleTestConnection}
                  size="large"
                  icon={<ApiOutlined />}
                >
                  测试连接
                </Button>
              </Space>
            </Form.Item>
          </Form>
        </Card>
      ),
    },
    {
      key: 'risk',
      label: (
        <span>
          <WarningOutlined />
          风险规则
        </span>
      ),
      children: (
        <Card loading={riskLoading} bordered={false} style={{ boxShadow: 'none' }}>
          {riskLevels.length > 0 ? (
            <Form form={riskForm} layout="vertical" disabled={savingRisk}>
              <Alert
                message="根据评估量表得分，系统将自动划分学生的风险等级。请根据实际需求设置各等级的分值区间。"
                type="warning"
                showIcon
                style={{ marginBottom: 20, borderRadius: 8 }}
              />
              <Table
                dataSource={riskLevels}
                rowKey="level"
                columns={riskColumns}
                pagination={false}
                size="middle"
                style={{ marginBottom: 20 }}
                scroll={{ x: 'max-content' }}
              />
              <Form.Item>
                <Button
                  type="primary"
                  loading={savingRisk}
                  onClick={handleSaveRisk}
                  size="large"
                >
                  保存风险配置
                </Button>
              </Form.Item>
            </Form>
          ) : (
            <Empty description="暂无风险等级配置数据，请联系平台管理员进行初始化配置。" />
          )}
        </Card>
      ),
    },
    {
      key: 'grades',
      label: (
        <span>
          <BankOutlined />
          年级管理
        </span>
      ),
      children: (
        <Card
          bordered={false}
          style={{ boxShadow: 'none' }}
          extra={
            <Button type="primary" icon={<PlusOutlined />} onClick={openAddGrade}>
              新增年级
            </Button>
          }
        >
          <Table
            dataSource={grades}
            rowKey="id"
            columns={gradeColumns}
            loading={gradesLoading}
            pagination={false}
            size="middle"
            scroll={{ x: 'max-content' }}
          />
        </Card>
      ),
    },
    {
      key: 'screen',
      label: (
        <span>
          <DesktopOutlined />
          数据大屏设置
        </span>
      ),
      children: (
        <Card loading={screenLoading} bordered={false} style={{ boxShadow: 'none' }}>
          <Alert
            message="设置数据大屏展示的标题和副标题信息，配置保存后将实时反映到大屏页面。"
            type="info"
            showIcon
            style={{ marginBottom: 20, borderRadius: 8 }}
          />
          <Form layout="vertical" style={{ maxWidth: 560 }} disabled={savingScreen}>
            <Form.Item label="大屏主标题">
              <Input
                placeholder="例如：学生心理健康监测数据大屏"
                value={screenConfig?.screen_title || ''}
                onChange={(e) =>
                  setScreenConfig((prev) => ({
                    ...(prev || { screen_title: '', screen_subtitle: '' }),
                    screen_title: e.target.value,
                  }))
                }
                size="large"
              />
            </Form.Item>
            <Form.Item label="大屏副标题">
              <Input
                placeholder="例如：2025年度第一学期测评数据"
                value={screenConfig?.screen_subtitle || ''}
                onChange={(e) =>
                  setScreenConfig((prev) => ({
                    ...(prev || { screen_title: '', screen_subtitle: '' }),
                    screen_subtitle: e.target.value,
                  }))
                }
                size="large"
              />
            </Form.Item>
            <Divider style={{ margin: '24px 0 16px' }} />
            <Form.Item>
              <Button
                type="primary"
                loading={savingScreen}
                onClick={handleSaveScreen}
                size="large"
              >
                保存大屏配置
              </Button>
            </Form.Item>
          </Form>
        </Card>
      ),
    },
    {
      key: 'about',
      label: (
        <span>
          <InfoCircleOutlined />
          关于系统
        </span>
      ),
      children: (
        <Card bordered={false} style={{ boxShadow: 'none' }}>
          <div style={{ textAlign: 'center', marginBottom: 32, padding: '32px 0' }}>
            <div
              style={{
                width: 72,
                height: 72,
                borderRadius: 18,
                background: 'linear-gradient(135deg, #d4a843, #c49635)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 20px',
                boxShadow: '0 4px 16px rgba(22, 119, 255, 0.3)',
              }}
            >
              <SafetyOutlined style={{ fontSize: 36, color: '#fff' }} />
            </div>
            <Title level={3} style={{ marginBottom: 4, color: '#1677ff' }}>
              金盾护苗 · 青少年关爱帮扶信息管理平台
            </Title>
            <Text type="secondary" style={{ fontSize: 16 }}>
              面向学校的青少年关爱帮扶信息管理平台
            </Text>
          </div>

          <Divider />

          <Descriptions
            bordered
            column={{ xs: 1, sm: 2 }}
            size="middle"
            labelStyle={{
              fontWeight: 500,
              background: '#fafafa',
              width: 140,
            }}
            contentStyle={{ background: '#fff' }}
          >
            <Descriptions.Item label="系统版本">
              <Tag color="blue">v1.0.0</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="发布日期">2025 年 1 月</Descriptions.Item>
            <Descriptions.Item label="前端框架">React 18 + TypeScript</Descriptions.Item>
            <Descriptions.Item label="UI 组件库">Ant Design 5</Descriptions.Item>
            <Descriptions.Item label="状态管理">Zustand</Descriptions.Item>
            <Descriptions.Item label="构建工具">Vite</Descriptions.Item>
            <Descriptions.Item label="后端框架">Python FastAPI</Descriptions.Item>
            <Descriptions.Item label="数据库">PostgreSQL</Descriptions.Item>
            <Descriptions.Item label="运行环境">Python 3.11+ / Node.js 18+</Descriptions.Item>
            <Descriptions.Item label="系统类型">B/S 架构 Web 应用</Descriptions.Item>
          </Descriptions>

          <Divider />

          <div
            style={{
              padding: 16,
              background: '#f6ffed',
              borderRadius: 10,
              border: '1px solid #b7eb8f',
            }}
          >
            <Space direction="vertical" size="small">
              <Text strong style={{ color: '#52c41a' }}>
                主要功能模块
              </Text>
              <Text type="secondary" style={{ fontSize: 13 }}>
                班级管理、学生管理、教师管理、问卷库管理、问卷任务发布、
                在线答题与质量检测、风险等级评估与预警、干预记录追踪、数据报表与可视化大屏
              </Text>
            </Space>
          </div>

          <Paragraph
            type="secondary"
            style={{ textAlign: 'center', marginTop: 32, fontSize: 12 }}
          >
            Copyright 2024-2025 · 金盾护苗 · 版权所有
          </Paragraph>
        </Card>
      ),
    },
  ];

  // ==================== render ====================

  return (
    <div>
      {/* 页面标题 */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 20,
          paddingBottom: 16,
          borderBottom: '1px solid #f0f0f0',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div
            style={{
              width: 4,
              height: 20,
              borderRadius: 2,
              background: 'linear-gradient(180deg, #1677ff, #4096ff)',
            }}
          />
          <Title level={5} style={{ margin: 0, fontWeight: 600, color: '#262626' }}>
            系统设置
          </Title>
        </div>
      </div>

      {/* Tab 页签 */}
      <Card style={{ borderRadius: 12 }} bodyStyle={{ padding: '8px 24px 24px' }}>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
          size="large"
          style={{ marginTop: -8 }}
        />
      </Card>

      {/* 新增年级弹窗 */}
      <Modal
        title="新增年级"
        open={gradeModalOpen}
        onOk={handleAddGrade}
        onCancel={() => setGradeModalOpen(false)}
        confirmLoading={addingGrade}
        destroyOnClose
        okText="确认添加"
        cancelText="取消"
      >
        <Form form={gradeForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="name"
            label="年级名称"
            rules={[{ required: true, message: '请输入年级名称' }]}
          >
            <Input placeholder="例如：一年级、七年级、高一" />
          </Form.Item>
          <Form.Item
            name="sort_order"
            label="排序"
            tooltip="数字越小越靠前显示"
          >
            <InputNumber min={0} style={{ width: '100%' }} placeholder="数字越小越靠前" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
