import { useEffect, useState } from "react"
import { Button, Popover, Slider, Tooltip } from "antd"
import { PictureOutlined } from "@ant-design/icons"
import { useAppContext } from "../../context/AppContext"
import './BackgroundPicker.css'

interface Picture {
    id: string
    name: string
    thumb: string
}

const BackgroundPicker: React.FC = () => {
    const { background, setBackground } = useAppContext()
    // Follows the slider while dragging, saved when released
    const [transparency, setTransparency] = useState(background.transparency)

    useEffect(() => setTransparency(background.transparency), [background.transparency])

    const [pictures, setPictures] = useState<Picture[]>([])

    async function loadPictures() {
        try {
            setPictures(await window.pywebview.api.list_backgrounds())
        } catch (e) {
            setPictures([])
        }
    }

    function save(next: { image: string | null, transparency: number }) {
        setBackground(next)
        try {
            window.pywebview.api.save_settings({ background: next })
        } catch (e) {
            // Not running inside the app, the choice just is not remembered
        }
    }

    const content = (
        <div className="bg-picker">
            <div className="bg-title">Background</div>
            <div className="bg-grid">
                <Tooltip title="Default">
                    <div
                        className={`bg-thumb bg-default${background.image === null ? ' selected' : ''}`}
                        onClick={() => save({ ...background, image: null })}
                    >
                        Default
                    </div>
                </Tooltip>
                {pictures.map(img => (
                    <Tooltip key={img.id} title={img.name}>
                        <div
                            className={`bg-thumb${background.image === img.id ? ' selected' : ''}`}
                            style={{ backgroundImage: `url(${img.thumb})` }}
                            onClick={() => save({ ...background, image: img.id })}
                        />
                    </Tooltip>
                ))}
            </div>
            <div className="bg-slider">
                <div className="bg-label">
                    <span>Transparency</span>
                    <span>{transparency}%</span>
                </div>
                <Slider
                    min={0}
                    max={100}
                    value={transparency}
                    disabled={background.image === null}
                    tooltip={{ open: false }}
                    onChange={setTransparency}
                    onChangeComplete={(value: number) => save({ ...background, transparency: value })}
                />
                <div className="bg-hint">Higher = the panels let more of the picture show through. Use Hide panels (F2) to see only the picture.</div>
            </div>
        </div>
    )

    return (
        <Popover content={content} trigger="click" placement="bottomRight" onOpenChange={(open) => { if (open && pictures.length === 0) loadPictures() }}>
            <Button className="bg-button" type="text" icon={<PictureOutlined />}>Background</Button>
        </Popover>
    )
}

export default BackgroundPicker
