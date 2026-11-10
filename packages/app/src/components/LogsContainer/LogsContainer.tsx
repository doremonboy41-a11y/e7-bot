import { useEffect, useRef } from "react";
import { Card } from "antd";
import { useAppContext } from "../../context/AppContext";
import './LogsContainer.css'

const lineClass = (line: string) => {
    if (line.includes(' ERROR ')) return 'log-line error'
    if (line.includes(' WARNING ')) return 'log-line warn'
    return 'log-line'
}

const Logs: React.FC = () => {
    const { logs } = useAppContext()
    const boxRef = useRef<HTMLDivElement>(null)

    // Keep the newest line in view without scrolling the whole window
    useEffect(() => {
        if (boxRef.current) {
            boxRef.current.scrollTop = boxRef.current.scrollHeight
        }
    }, [logs])

    return (
        <Card className="logs" title="Logs" size="small">
            <div className="log-box" ref={boxRef}>
                {logs.length === 0 ? <div className="log-empty">No logs yet. Press Confirm &amp; Start.</div> : null}
                {logs.map((line, i) => <div key={i} className={lineClass(line)}>{line}</div>)}
            </div>
        </Card>
    )
}

export default Logs
