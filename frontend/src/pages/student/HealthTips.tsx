import { Card, Typography, Row, Col, Tag, Space, Divider } from 'antd';
import {
  HeartOutlined,
  SmileOutlined,
  PhoneOutlined,
  SafetyOutlined,
  TeamOutlined,
  ReadOutlined,
  ThunderboltOutlined,
  CustomerServiceOutlined,
} from '@ant-design/icons';

const { Title, Paragraph, Text } = Typography;

const tipCards = [
  {
    icon: <SmileOutlined style={{ fontSize: 28, color: '#4A90D9' }} />,
    title: '认识自己的情绪',
    color: '#4A90D9',
    content:
      '每个人都会有开心、难过、紧张、生气等各种情绪，这些都是正常的。学会觉察自己的情绪变化，是照顾自己的第一步。当你能说出"我现在有点焦虑"的时候，其实已经在进步了。',
  },
  {
    icon: <ThunderboltOutlined style={{ fontSize: 28, color: '#67C23A' }} />,
    title: '学会释放压力',
    color: '#67C23A',
    content:
      '学习压力大的时候，不要一个人扛。可以试试听听音乐、画画、运动，或者和朋友聊聊天。找到适合自己的减压方式，把它变成一种习惯，你会发现生活轻松很多。',
  },
  {
    icon: <TeamOutlined style={{ fontSize: 28, color: '#E6A23C' }} />,
    title: '经营健康的人际关系',
    color: '#E6A23C',
    content:
      '好的朋友会让你感到被理解和支持。学会倾听他人，也勇敢表达自己的想法。如果一段关系让你感到不舒服，可以寻求信任的大人帮助。你值得被友善对待。',
  },
  {
    icon: <HeartOutlined style={{ fontSize: 28, color: '#F56C6C' }} />,
    title: '好好照顾自己',
    color: '#F56C6C',
    content:
      '保证充足的睡眠、规律的饮食和适度的运动，这些看似简单的事情对心理健康非常重要。给自己留出休息和放松的时间，不必时刻追求完美，"已经很好了"也是一种了不起。',
  },
  {
    icon: <ReadOutlined style={{ fontSize: 28, color: '#909399' }} />,
    title: '培养积极的思维方式',
    color: '#909399',
    content:
      '遇到困难时，试着换个角度思考。与其想"我做不到"，不如想"我可以试试看"。失败不代表你不行，它只是告诉你还有成长的空间。每天记录一件让自己开心的小事，你会发现自己比想象中更棒。',
  },
];

const emotionTips = [
  {
    emoji: '🫁',
    title: '深呼吸放松法',
    description: '慢慢吸气4秒，屏住呼吸4秒，再缓缓呼气6秒。重复3-5次，让身体和情绪都慢慢平静下来。',
  },
  {
    emoji: '📝',
    title: '写日记或画画',
    description: '把心里的想法和感受写下来或者画出来，不需要写得多好，只要是真实的就好。这是一种很好的自我表达方式。',
  },
  {
    emoji: '💬',
    title: '找人倾诉',
    description: '和信任的朋友、家人或者老师说说话。有时候只需要一个人认真听你说，心里就会舒服很多。说出来，不丢人。',
  },
  {
    emoji: '🏃',
    title: '运动释放',
    description: '跑步、打球、跳绳、散步……运动能让大脑分泌让人快乐的物质。哪怕只是出门走走，心情也会好起来。',
  },
];

const helpChannels = [
  {
    icon: <SafetyOutlined style={{ fontSize: 24, color: '#4A90D9' }} />,
    title: '学校心理老师',
    description: '学校里有专门的心理辅导老师，他们很有经验，会认真倾听你的困扰，并且为你保密。你可以主动预约。',
  },
  {
    icon: <PhoneOutlined style={{ fontSize: 24, color: '#67C23A' }} />,
    title: '12355 青少年服务热线',
    description: '这是一条专门为青少年设立的热线电话，有专业的心理咨询师在线，免费、保密，随时可以拨打。',
  },
  {
    icon: <TeamOutlined style={{ fontSize: 24, color: '#E6A23C' }} />,
    title: '信任的老师',
    description: '班主任或者其他你信任的老师，都可以成为你倾诉的对象。老师关心你的成长，愿意帮助你。',
  },
  {
    icon: <HeartOutlined style={{ fontSize: 24, color: '#F56C6C' }} />,
    title: '爸爸妈妈或家人',
    description: '家人是最关心你的人。如果你觉得有困扰，试着和他们说说，即使一开始有点难开口，但他们一定想了解你的感受。',
  },
];

export default function HealthTips() {
  return (
    <div style={{ paddingBottom: 32 }}>
      <Title level={4} style={{ marginBottom: 8 }}>
        <HeartOutlined style={{ color: '#F56C6C', marginRight: 8 }} />
        心理健康小课堂
      </Title>
      <Paragraph type="secondary" style={{ marginBottom: 24 }}>
        照顾好自己的心灵，和照顾身体一样重要。这里有一些温暖的小知识，希望能帮到你。
      </Paragraph>

      {/* Section 1: 心理健康小知识 */}
      <Title level={5}>心理健康小知识</Title>
      <Row gutter={[16, 16]} style={{ marginBottom: 32 }}>
        {tipCards.map((tip) => (
          <Col xs={24} sm={12} md={8} key={tip.title}>
            <Card
              hoverable
              style={{ height: '100%', borderRadius: 12 }}
              bodyStyle={{ padding: 20 }}
            >
              <Space direction="vertical" size={12} style={{ width: '100%' }}>
                {tip.icon}
                <Text strong style={{ fontSize: 15, color: tip.color }}>
                  {tip.title}
                </Text>
                <Paragraph
                  type="secondary"
                  style={{ fontSize: 13, lineHeight: 1.8, marginBottom: 0 }}
                >
                  {tip.content}
                </Paragraph>
              </Space>
            </Card>
          </Col>
        ))}
      </Row>

      {/* Section 2: 情绪管理技巧 */}
      <Title level={5}>情绪管理小技巧</Title>
      <Card style={{ marginBottom: 32, borderRadius: 12 }}>
        <Row gutter={[16, 16]}>
          {emotionTips.map((tip) => (
            <Col xs={24} sm={12} key={tip.title}>
              <Space align="start" size={12}>
                <Text style={{ fontSize: 22 }}>{tip.emoji}</Text>
                <div>
                  <Text strong style={{ fontSize: 14 }}>
                    {tip.title}
                  </Text>
                  <Paragraph
                    type="secondary"
                    style={{ fontSize: 13, lineHeight: 1.7, marginBottom: 0, marginTop: 4 }}
                  >
                    {tip.description}
                  </Paragraph>
                </div>
              </Space>
            </Col>
          ))}
        </Row>
      </Card>

      {/* Section 3: 寻求帮助的途径 */}
      <Title level={5}>寻求帮助的途径</Title>
      <Paragraph type="secondary" style={{ marginBottom: 16 }}>
        如果你感到困扰，请记住：主动寻求帮助是勇敢的表现，而不是软弱。
      </Paragraph>
      <Row gutter={[16, 16]} style={{ marginBottom: 32 }}>
        {helpChannels.map((channel) => (
          <Col xs={24} sm={12} md={6} key={channel.title}>
            <Card
              hoverable
              style={{ height: '100%', borderRadius: 12, textAlign: 'center' }}
              bodyStyle={{ padding: 20 }}
            >
              <div style={{ marginBottom: 12 }}>{channel.icon}</div>
              <Text strong style={{ display: 'block', marginBottom: 8, fontSize: 14 }}>
                {channel.title}
              </Text>
              <Paragraph
                type="secondary"
                style={{ fontSize: 12, lineHeight: 1.7, marginBottom: 0 }}
              >
                {channel.description}
              </Paragraph>
            </Card>
          </Col>
        ))}
      </Row>

      {/* Section 4: 24小时心理援助热线 */}
      <Card
        style={{
          borderRadius: 12,
          background: 'linear-gradient(135deg, #4A90D9 0%, #67C23A 100%)',
          border: 'none',
        }}
        bodyStyle={{ padding: '24px 20px' }}
      >
        <Space
          direction="vertical"
          align="center"
          style={{ width: '100%', color: '#fff' }}
          size={16}
        >
          <CustomerServiceOutlined style={{ fontSize: 32 }} />
          <Text strong style={{ fontSize: 18, color: '#fff' }}>
            24小时心理援助热线
          </Text>
          <Text style={{ fontSize: 13, color: 'rgba(255,255,255,0.85)' }}>
            随时可以拨打，免费保密，有人愿意听你说
          </Text>
          <Space size={24} wrap style={{ justifyContent: 'center' }}>
            <Tag
              color="#fff"
              style={{
                fontSize: 20,
                padding: '8px 20px',
                color: '#4A90D9',
                fontWeight: 700,
                borderRadius: 20,
                border: 'none',
              }}
            >
              <PhoneOutlined style={{ marginRight: 6 }} />
              12355
            </Tag>
            <Tag
              color="#fff"
              style={{
                fontSize: 20,
                padding: '8px 20px',
                color: '#67C23A',
                fontWeight: 700,
                borderRadius: 20,
                border: 'none',
              }}
            >
              <PhoneOutlined style={{ marginRight: 6 }} />
              400-161-9995
            </Tag>
          </Space>
          <Paragraph
            style={{
              color: 'rgba(255,255,255,0.75)',
              fontSize: 12,
              marginBottom: 0,
              marginTop: 4,
            }}
          >
            你不是一个人，当你需要的时候，请勇敢拨打
          </Paragraph>
        </Space>
      </Card>

      <Divider />
      <Paragraph type="secondary" style={{ textAlign: 'center', fontSize: 12 }}>
        记住：关注自己的心理健康，是每个人都值得做的事情。你很棒，继续加油。
      </Paragraph>
    </div>
  );
}
