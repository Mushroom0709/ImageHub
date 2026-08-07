import { useNavigate } from 'react-router-dom'

export function MobileNav() {
  const navigate = useNavigate()

  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    navigate('/login')
  }

  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-white dark:bg-zinc-900 border-t border-zinc-200 dark:border-zinc-800 h-14 flex items-center justify-around">
      <button className="flex flex-col items-center text-teal-600 text-[10px] gap-0.5">
        <span className="text-lg">🏠</span>
        首页
      </button>
      <button className="flex flex-col items-center text-zinc-500 text-[10px] gap-0.5">
        <span className="text-lg">🔍</span>
        搜索
      </button>
      <button className="flex flex-col items-center text-zinc-500 text-[10px] gap-0.5">
        <span className="text-lg">⭐</span>
        星标
      </button>
      <button className="flex flex-col items-center text-zinc-500 text-[10px] gap-0.5">
        <span className="text-lg">🔗</span>
        采集
      </button>
      <button onClick={handleLogout} className="flex flex-col items-center text-zinc-500 text-[10px] gap-0.5">
        <span className="text-lg">👤</span>
        退出
      </button>
    </nav>
  )
}
