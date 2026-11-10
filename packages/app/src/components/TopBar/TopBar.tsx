import { Badge, Tag } from "antd";
import { Button, Tooltip } from "antd";
import { EyeInvisibleOutlined, EyeOutlined, ShoppingOutlined } from "@ant-design/icons";
import { useAppContext } from "../../context/AppContext";
import BackgroundPicker from '../BackgroundPicker/BackgroundPicker'
import './TopBar.css'

const STATUS = {
    idle: { badge: 'default', text: 'Idle' },
    running: { badge: 'processing', text: 'Running' },
    finished: { badge: 'success', text: 'Finished' },
    stopped: { badge: 'error', text: 'Stopped' },
} as const

const TopBar: React.FC = () => {
    const { appVersion, status, devMode, background, panelsHidden, setPanelsHidden } = useAppContext()
    const current = STATUS[status]

    return (
        <header className="topbar">
            <div className="brand">
                <ShoppingOutlined className="brand-icon" />
                <div>
                    <div className="brand-title">Epic7 Bot</div>
                    <div className="brand-sub">Secret Shop Auto Buy · by Kazari</div>
                </div>
            </div>
            <div className="meta">
                {background.image !== null ?
                    <Tooltip title="Show only the background picture (F2, Esc to come back)">
                        <Button
                            className="bg-button"
                            type="text"
                            icon={panelsHidden ? <EyeOutlined /> : <EyeInvisibleOutlined />}
                            onClick={() => setPanelsHidden(v => !v)}
                        >
                            {panelsHidden ? 'Show panels' : 'Hide panels'}
                        </Button>
                    </Tooltip>
                    : null}
                <BackgroundPicker />
                {devMode ? <Tag color="purple">Dev Mode</Tag> : null}
                <Badge status={current.badge} text={<span className="status-text">{current.text}</span>} />
                {appVersion ? <Tag bordered={false}>{appVersion}</Tag> : null}
            </div>
        </header>
    )
}

export default TopBar
