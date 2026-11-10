import { Card, Progress } from "antd";
import { useAppContext } from "../../context/AppContext";
import { formatNumber } from "../../utils/format";
import './StatsContainer.css'

const Tile: React.FC<{ label: string, value: number, limit?: number | null, highlight?: boolean }> = ({ label, value, limit, highlight }) => {
    const hasLimit = limit !== undefined && limit !== null
    const percent = hasLimit && limit > 0 ? Math.min(100, Math.round((value / limit) * 100)) : 0

    return (
        <div className={`tile${highlight ? ' highlight' : ''}`}>
            <div className="tile-label">{label}</div>
            <div className="tile-value">
                {formatNumber(value)}
                {hasLimit ? <span className="tile-limit"> / {formatNumber(limit)}</span> : null}
            </div>
            {hasLimit ? <Progress percent={percent} size="small" showInfo={false} /> : null}
        </div>
    )
}

const StatsContainer: React.FC = () => {
    const { stats } = useAppContext()

    return (
        <Card className="stats" title="Summary" size="small">
            <div className="tiles">
                <Tile label="Refreshes" value={stats?.refreshes_count ?? 0} />
                <Tile label="Skystones used" value={stats?.skystones_used ?? 0} limit={stats?.max_skystones} highlight />
                <Tile label="Gold used" value={stats?.gold_used ?? 0} limit={stats?.max_gold} highlight />
                <Tile label="Covenants bought" value={stats?.covenant_count ?? 0} />
                <Tile label="Mystics bought" value={stats?.mystic_count ?? 0} />
                {stats?.buy_friendship ? <Tile label="Friendship bought" value={stats?.friendship_count ?? 0} /> : null}
            </div>
        </Card>
    )
}

export default StatsContainer
