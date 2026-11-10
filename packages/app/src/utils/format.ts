export const formatNumber = (value?: number | string | null) =>
    `${value ?? ''}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
