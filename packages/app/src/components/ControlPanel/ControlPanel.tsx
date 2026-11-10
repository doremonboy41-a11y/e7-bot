import { useEffect, useRef, useState } from "react"
import { Button, Card, Checkbox, InputNumber, Popconfirm, Select, Space, Tag, Tooltip } from "antd"
import { CheckOutlined, InfoCircleOutlined, PauseCircleOutlined } from "@ant-design/icons"
import { useAppContext } from "../../context/AppContext"
import type { LimitMode, ShopOptions } from "../../context/AppContext"
import { formatNumber } from "../../utils/format"
import './ControlPanel.css'

const SKYSTONES_PER_REFRESH = 3
const COVENANT_PRICE = 184000
const MYSTIC_PRICE = 280000
const MIN_GOLD = Math.min(COVENANT_PRICE, MYSTIC_PRICE)
const FRIENDSHIP_PRICE = 18000
const MAX_SPEED = 10
const SPEED_OPTIONS = Array.from({ length: MAX_SPEED }, (_, i) => ({ value: i + 1, label: `${i + 1}x` }))
// Written to the logs by the bot when it stops by itself (a limit was reached)
const FINISHED_MARKER = 'Secret Shop finished'

const DEFAULT_OPTIONS: ShopOptions = { speed: 1, mode: 'none', amount: null, buyFriendship: false }

const ControlPanel: React.FC = () => {
    const {
        setLogs,
        setStats,
        status,
        setStatus,
        fastMode,
        setFastMode,
        currentScreen,
        setCurrentScreen,
        devMode,
    } = useAppContext()

    // What is being edited
    const [speed, setSpeed] = useState(DEFAULT_OPTIONS.speed)
    const [mode, setMode] = useState<LimitMode>(DEFAULT_OPTIONS.mode)
    const [skystoneAmount, setSkystoneAmount] = useState<number | null>(null)
    const [goldAmount, setGoldAmount] = useState<number | null>(null)
    const [buyFriendship, setBuyFriendship] = useState(DEFAULT_OPTIONS.buyFriendship)
    // What the bot runs with: only changes when Confirm is pressed
    const [applied, setApplied] = useState<ShopOptions>(DEFAULT_OPTIONS)

    const pollRef = useRef<number | null>(null)
    const logsRef = useRef('')

    const amount = mode === 'skystone' ? skystoneAmount : mode === 'gold' ? goldAmount : null
    const draft: ShopOptions = { speed, mode, amount, buyFriendship }
    const minAmount = mode === 'skystone' ? SKYSTONES_PER_REFRESH : MIN_GOLD
    const amountOk = mode === 'none' || (amount !== null && amount >= minAmount)
    const dirty = draft.speed !== applied.speed || draft.mode !== applied.mode || draft.amount !== applied.amount || draft.buyFriendship !== applied.buyFriendship

    useEffect(() => stopPolling, [])

    function stopPolling() {
        if (pollRef.current !== null) {
            window.clearInterval(pollRef.current)
            pollRef.current = null
        }
    }

    async function poll() {
        try {
            // Read before the logs, so the last lines written before exiting are not missed
            const alive: boolean = await window.pywebview.api.is_running()
            const text: string = await window.pywebview.api.get_logs()
            if (text !== logsRef.current) {
                logsRef.current = text
                setLogs(text.split('\n').filter(line => line.trim() !== ''))
            }
            const res = await window.pywebview.api.get_summary('secret_shop')
            if (res) {
                setStats(res)
            }
            if (text.includes(FINISHED_MARKER)) {
                setStatus('finished')
                stopPolling()
            } else if (!alive) {
                // The bot exited by itself (e.g. no emulator or no Epic Seven found), the reason is in the logs
                setStatus('stopped')
                stopPolling()
            }
        } catch (e) {
            // The bot may not have written its files yet, try again on the next tick
        }
    }

    function startPolling() {
        stopPolling()
        pollRef.current = window.setInterval(poll, 500)
    }

    function buildArgs(options: ShopOptions) {
        return {
            '--fast': fastMode,
            '--current': currentScreen,
            '--speed': options.speed,
            '--max-skystones': options.mode === 'skystone' ? options.amount : null,
            '--max-gold': options.mode === 'gold' ? options.amount : null,
            '--buy-friendship': options.buyFriendship,
        }
    }

    // Starting stops the bot that is already running (done in view.py)
    async function launch(options: ShopOptions) {
        stopPolling()
        logsRef.current = ''
        setLogs([])
        setStats(null)
        setStatus('running')
        try {
            await window.pywebview.api.start_shop(buildArgs(options))
            startPolling()
        } catch (e) {
            setStatus('idle')
            setLogs([`Could not start the bot: ${String(e)}`])
        }
    }

    async function handleStop() {
        stopPolling()
        try {
            await window.pywebview.api.stop_running_command()
        } catch (e) {
            // Nothing was running
        }
        await poll()
        setStatus('idle')
        setLogs(prev => [...prev, 'Stopped by user'])
    }

    async function handleConfirm() {
        setApplied(draft)
        await launch(draft)
    }

    return (
        <Card
            className="controls"
            title="Controls"
            size="small"
            extra={dirty ? <Tag color="orange">Unconfirmed changes</Tag> : null}
        >
            {devMode ?
                <div className="toolbar">
                    <Space size="middle">
                        <Popconfirm
                            overlayStyle={{ maxWidth: "500px" }}
                            title="Are you sure you want to use Fast Mode?"
                            description={<div>
                                <p style={{ margin: 0 }}>Turns on Fast Mode, which makes the each step of the command faster.</p>
                                <p style={{ margin: 0 }}>Warning: It's currently very unstable and requires a high-end PC to work properly.</p>
                            </div>}
                            onConfirm={() => setFastMode(true)}
                            onCancel={() => setFastMode(false)}
                            disabled={fastMode === true}
                            okText="Yes"
                            cancelText="No"
                        >
                            <Checkbox checked={fastMode} onClick={() => { if (fastMode) setFastMode(false) }}>
                                Fast Mode
                            </Checkbox>
                        </Popconfirm>
                        <Popconfirm
                            overlayStyle={{ maxWidth: "500px" }}
                            title="Are you sure you want to use Skip Lobby?"
                            description={<div>
                                <p style={{ margin: 0 }}>Turns on Skip lobby, which skips the first steps of the current command to get to the desired screen of the command. User must perform theses skipped steps manually.</p>
                                <p style={{ margin: 0 }}>Ex: On Shop Command it would skip the steps to click on the bartender and consider that the screen on the emulator is already on the shop.</p>
                            </div>}
                            onConfirm={() => setCurrentScreen(true)}
                            onCancel={() => setCurrentScreen(false)}
                            disabled={currentScreen === true}
                            okText="Yes"
                            cancelText="No"
                        >
                            <Checkbox checked={currentScreen} onChange={() => { if (currentScreen) setCurrentScreen(false) }}>
                                Skip Lobby
                            </Checkbox>
                        </Popconfirm>
                    </Space>

                </div>
                : null}

            <div className="settings">
                <div className="field">
                    <div className="label">
                        Speed
                        <Tooltip title="Divides every wait of the bot. 1x is the original speed. Higher speeds are less stable: if clicks start missing, lower it.">
                            <InfoCircleOutlined className="info" />
                        </Tooltip>
                    </div>
                    <Select value={speed} onChange={setSpeed} options={SPEED_OPTIONS} style={{ width: 96 }} />
                    {speed > 5 ? <div className="hint warn">High speed, clicks may be missed</div> : null}
                </div>

                <div className="field">
                    <div className="label">
                        Refresh limit
                        <Tooltip title="Tick one option to stop the bot after spending that amount. Leave both unticked to refresh until you press Stop.">
                            <InfoCircleOutlined className="info" />
                        </Tooltip>
                    </div>
                    <div className={`limit-row${mode === 'gold' ? ' dimmed' : ''}`}>
                        <Checkbox
                            className="limit-check"
                            checked={mode === 'skystone'}
                            disabled={mode === 'gold'}
                            onChange={(e) => setMode(e.target.checked ? 'skystone' : 'none')}
                        >
                            Skystone
                        </Checkbox>
                        <InputNumber
                            min={SKYSTONES_PER_REFRESH}
                            step={SKYSTONES_PER_REFRESH}
                            precision={0}
                            value={skystoneAmount}
                            onChange={(value) => setSkystoneAmount(value)}
                            disabled={mode !== 'skystone'}
                            placeholder="Amount"
                            style={{ width: 150 }}
                        />
                        <span className="hint inline">
                            {skystoneAmount !== null
                                ? `= ${Math.floor(skystoneAmount / SKYSTONES_PER_REFRESH)} refreshes`
                                : `${SKYSTONES_PER_REFRESH} skystones = 1 refresh`}
                        </span>
                    </div>
                    <div className={`limit-row${mode === 'skystone' ? ' dimmed' : ''}`}>
                        <Checkbox
                            className="limit-check"
                            checked={mode === 'gold'}
                            disabled={mode === 'skystone'}
                            onChange={(e) => setMode(e.target.checked ? 'gold' : 'none')}
                        >
                            Gold
                        </Checkbox>
                        <InputNumber
                            min={MIN_GOLD}
                            step={MIN_GOLD}
                            precision={0}
                            value={goldAmount}
                            onChange={(value) => setGoldAmount(value)}
                            formatter={(value) => formatNumber(value)}
                            parser={(value) => Number((value ?? '').replace(/,/g, ''))}
                            disabled={mode !== 'gold'}
                            placeholder="Amount"
                            style={{ width: 150 }}
                        />
                        <span className="hint inline">
                            Covenant {formatNumber(COVENANT_PRICE)} · Mystic {formatNumber(MYSTIC_PRICE)}
                        </span>
                    </div>
                    {mode === 'none' ? <div className="hint">Unlimited: refreshes until you press Stop.</div> : null}
                    {mode !== 'none' && !amountOk ? <div className="hint warn">Enter at least {formatNumber(minAmount)}.</div> : null}
                </div>

                <div className="field">
                    <div className="label">
                        Buy
                        <Tooltip title="Covenant and Mystic bookmarks are always bought. Tick this to also buy Friendship Points whenever they appear after a refresh.">
                            <InfoCircleOutlined className="info" />
                        </Tooltip>
                    </div>
                    <div className="limit-row">
                        <Checkbox checked={buyFriendship} onChange={(e) => setBuyFriendship(e.target.checked)}>
                            Friendship Points
                        </Checkbox>
                    </div>
                    <div className="hint">50 points · {formatNumber(FRIENDSHIP_PRICE)} gold each</div>
                </div>

                <div className="field actions">
                    <div className="action-row">
                        <Button type="primary" block icon={<CheckOutlined />} disabled={!amountOk} onClick={handleConfirm}>
                            {status === 'running' ? <>Confirm &amp; Restart</> : <>Confirm &amp; Start</>}
                        </Button>
                    </div>
                    <div className="action-row">
                        <Button danger block icon={<PauseCircleOutlined />} disabled={status !== 'running'} onClick={handleStop}>
                            Stop
                        </Button>
                    </div>
                    <div className="hint">Confirm stops the bot and starts it again with these settings.</div>
                </div>
            </div>
        </Card>
    )
}

export default ControlPanel
