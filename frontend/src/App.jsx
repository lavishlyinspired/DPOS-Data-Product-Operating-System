import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Products from './pages/Products'
import ProductDetail from './pages/ProductDetail'
import Domains from './pages/Domains'
import Contracts from './pages/Contracts'
import Incidents from './pages/Incidents'
import Lineage from './pages/Lineage'
import Pipelines from './pages/Pipelines'
import Policies from './pages/Policies'
import Marketplace from './pages/Marketplace'
import Agents from './pages/Agents'
import Intelligence from './pages/Intelligence'
import Ingestion from './pages/Ingestion'
import HumanReview from './pages/HumanReview'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="products" element={<Products />} />
          <Route path="products/:id" element={<ProductDetail />} />
          <Route path="domains" element={<Domains />} />
          <Route path="contracts" element={<Contracts />} />
          <Route path="incidents" element={<Incidents />} />
          <Route path="lineage" element={<Lineage />} />
          <Route path="pipelines" element={<Pipelines />} />
          <Route path="policies" element={<Policies />} />
          <Route path="marketplace" element={<Marketplace />} />
          <Route path="agents" element={<Agents />} />
          <Route path="intelligence" element={<Intelligence />} />
          <Route path="ingestion" element={<Ingestion />} />
          <Route path="human-review" element={<HumanReview />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
