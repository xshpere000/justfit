import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/zh-cn'

// 配置 dayjs
dayjs.locale('zh-cn')
dayjs.extend(relativeTime)

export default dayjs
