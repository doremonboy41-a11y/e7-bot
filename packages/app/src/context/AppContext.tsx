import React, { useContext, useState } from "react";

export interface ShopStats {
    covenant_count: number
    mystic_count: number
    friendship_count: number
    buy_friendship: boolean
    refreshes_count: number
    skystones_used: number
    gold_used: number
    max_skystones: number | null
    max_gold: number | null
}

// 'stopped' = the bot exited by itself without finishing (e.g. no emulator / no Epic Seven found)
export type BotStatus = 'idle' | 'running' | 'finished' | 'stopped'

// Which resource limits the refreshes. 'none' = unlimited
export type LimitMode = 'none' | 'skystone' | 'gold'

export interface ShopOptions {
    speed: number
    mode: LimitMode
    amount: number | null
    buyFriendship: boolean
}

export interface BackgroundSettings {
    image: string | null // file name of the chosen image, null = default
    transparency: number // 0-100, how much the panels let the picture show through
}

interface AppContextInterface {
    background: BackgroundSettings
    setBackground: React.Dispatch<React.SetStateAction<BackgroundSettings>>
    logs: string[]
    setLogs: React.Dispatch<React.SetStateAction<string[]>>
    stats: ShopStats | null
    setStats: React.Dispatch<React.SetStateAction<ShopStats | null>>
    status: BotStatus
    setStatus: React.Dispatch<React.SetStateAction<BotStatus>>
    appVersion: string
    setAppVersion: React.Dispatch<React.SetStateAction<string>>
    fastMode: boolean
    setFastMode: React.Dispatch<React.SetStateAction<boolean>>
    currentScreen: boolean
    setCurrentScreen: React.Dispatch<React.SetStateAction<boolean>>
    devMode: boolean
    setDevMode: React.Dispatch<React.SetStateAction<boolean>>
    // Shows only the background picture (panels hidden)
    panelsHidden: boolean
    setPanelsHidden: React.Dispatch<React.SetStateAction<boolean>>
}

export const AppContext = React.createContext<AppContextInterface>({
    background: { image: null, transparency: 70 },
    setBackground: () => { },
    logs: [],
    setLogs: () => { },
    stats: null,
    setStats: () => { },
    status: 'idle',
    setStatus: () => { },
    appVersion: '',
    setAppVersion: () => { },
    fastMode: false,
    setFastMode: () => { },
    currentScreen: false,
    setCurrentScreen: () => { },
    devMode: false,
    setDevMode: () => { },
    panelsHidden: false,
    setPanelsHidden: () => { },
});

export const AppProvider = ({ children }: { children: any }) => {
    const [logs, setLogs] = useState<string[]>([])
    const [stats, setStats] = useState<ShopStats | null>(null)
    const [status, setStatus] = useState<BotStatus>('idle')
    const [appVersion, setAppVersion] = useState('')
    const [fastMode, setFastMode] = useState(false)
    const [currentScreen, setCurrentScreen] = useState(false)
    const [devMode, setDevMode] = useState(false)
    const [background, setBackground] = useState<BackgroundSettings>({ image: null, transparency: 70 })
    const [panelsHidden, setPanelsHidden] = useState(false)

    return (
        <AppContext.Provider value={{
            background,
            setBackground,
            logs,
            setLogs,
            stats,
            setStats,
            status,
            setStatus,
            appVersion,
            setAppVersion,
            fastMode,
            setFastMode,
            currentScreen,
            setCurrentScreen,
            devMode,
            setDevMode,
            panelsHidden,
            setPanelsHidden
        }}>
            {children}
        </AppContext.Provider>
    )
}

export const useAppContext = () => useContext(AppContext);
