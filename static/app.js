// ============================================================
// FinBot - Dashboard JavaScript
// ============================================================

const API_BASE = '/api';
let token = localStorage.getItem('token');
let usuario = JSON.parse(localStorage.getItem('usuario') || '{}');
let mesAtual = new Date().getMonth() + 1;
let anoAtual = new Date().getFullYear();
let filtros = { categoria: '', forma_pagamento: '', tipo: '' };

// ============================================================
// FUNÇÕES DE AUTENTICAÇÃO
// ============================================================

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('usuario');
    window.location.href = '/login';
}

function getHeaders() {
    return {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    };
}

// ============================================================
// FUNÇÕES DE CARREGAMENTO
// ============================================================

async function carregarCategorias() {
    try {
        const response = await fetch(`${API_BASE}/categorias`, { headers: getHeaders() });
        if (!response.ok) throw new Error('Erro ao carregar categorias');
        const categorias = await response.json();
        
        const select = document.getElementById('filtroCategoria');
        select.innerHTML = '<option value="">Todas</option>';
        categorias.forEach(c => {
            const option = document.createElement('option');
            option.value = c.nome;
            option.textContent = c.nome;
            select.appendChild(option);
        });
        
        select.addEventListener('change', (e) => {
            filtros.categoria = e.target.value;
            carregarDados();
        });
    } catch (err) {
        console.error(err);
    }
}

async function carregarResumo() {
    try {
        const response = await fetch(`${API_BASE}/resumo?mes=${mesAtual}&ano=${anoAtual}`, {
            headers: getHeaders()
        });
        if (!response.ok) throw new Error('Erro ao carregar resumo');
        const data = await response.json();
        
        document.getElementById('totalReceitas').textContent = `R$ ${data.receitas.toFixed(2)}`;
        document.getElementById('totalDespesas').textContent = `R$ ${data.despesas.toFixed(2)}`;
        document.getElementById('totalSaldo').textContent = `R$ ${data.saldo.toFixed(2)}`;
        
        return data;
    } catch (err) {
        console.error(err);
        if (err.message.includes('401')) logout();
    }
}

async function carregarTransacoes() {
    try {
        let url = `${API_BASE}/transacoes?mes=${mesAtual}&ano=${anoAtual}`;
        if (filtros.categoria) url += `&categoria=${encodeURIComponent(filtros.categoria)}`;
        if (filtros.forma_pagamento) url += `&forma_pagamento=${filtros.forma_pagamento}`;
        if (filtros.tipo) url += `&tipo=${filtros.tipo}`;
        
        const response = await fetch(url, { headers: getHeaders() });
        if (!response.ok) throw new Error('Erro ao carregar transações');
        const transacoes = await response.json();
        
        document.getElementById('totalTransacoes').textContent = `${transacoes.length} registros`;
        
        const tbody = document.getElementById('transacoesBody');
        tbody.innerHTML = '';
        transacoes.forEach(t => {
            const tr = document.createElement('tr');
            const tipoClass = t.tipo === 'R' ? 'text-success' : 'text-danger';
            const tipoEmoji = t.tipo === 'R' ? '📈' : '📉';
            tr.innerHTML = `
                <td>${t.data}</td>
                <td>${t.descricao || '-'}</td>
                <td>${t.categoria}</td>
                <td>${t.forma_pagamento || '-'}</td>
                <td class="${tipoClass}">${tipoEmoji} R$ ${t.valor.toFixed(2)}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary edit-btn" data-id="${t.id}">✏️</button>
                    <button class="btn btn-sm btn-outline-danger delete-btn" data-id="${t.id}">🗑️</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
        
        document.querySelectorAll('.edit-btn').forEach(btn => {
            btn.addEventListener('click', () => abrirEdicao(parseInt(btn.dataset.id)));
        });
        document.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', () => confirmarExclusao(parseInt(btn.dataset.id)));
        });
    } catch (err) {
        console.error(err);
        if (err.message.includes('401')) logout();
    }
}

async function abrirEdicao(id) {
    try {
        const response = await fetch(`${API_BASE}/transacoes?mes=${mesAtual}&ano=${anoAtual}`, {
            headers: getHeaders()
        });
        const transacoes = await response.json();
        const t = transacoes.find(item => item.id === id);
        if (!t) {
            alert('Transação não encontrada');
            return;
        }
        
        document.getElementById('editId').value = t.id;
        document.getElementById('editValor').value = t.valor;
        document.getElementById('editDescricao').value = t.descricao || '';
        document.getElementById('editCategoria').value = t.categoria;
        document.getElementById('editForma').value = t.forma_pagamento || '';
        document.getElementById('editData').value = t.data.split('/').reverse().join('-');
        
        const modal = new bootstrap.Modal(document.getElementById('editModal'));
        modal.show();
    } catch (err) {
        console.error(err);
        alert('Erro ao carregar dados para edição');
    }
}

async function salvarEdicao() {
    const id = parseInt(document.getElementById('editId').value);
    const dados = {
        valor: parseFloat(document.getElementById('editValor').value),
        descricao: document.getElementById('editDescricao').value,
        categoria: document.getElementById('editCategoria').value,
        forma_pagamento: document.getElementById('editForma').value,
        data: document.getElementById('editData').value.split('-').reverse().join('/')
    };
    
    try {
        const response = await fetch(`${API_BASE}/transacoes/${id}`, {
            method: 'PUT',
            headers: getHeaders(),
            body: JSON.stringify(dados)
        });
        
        if (!response.ok) throw new Error('Erro ao atualizar transação');
        
        const modal = bootstrap.Modal.getInstance(document.getElementById('editModal'));
        modal.hide();
        
        await carregarDados();
        alert('✅ Transação atualizada com sucesso!');
    } catch (err) {
        console.error(err);
        alert('❌ Erro ao atualizar transação');
    }
}

async function confirmarExclusao(id) {
    if (!confirm('Tem certeza que deseja apagar esta transação?')) return;
    
    try {
        const response = await fetch(`${API_BASE}/transacoes/${id}`, {
            method: 'DELETE',
            headers: getHeaders()
        });
        
        if (!response.ok) throw new Error('Erro ao apagar transação');
        
        await carregarDados();
        alert('✅ Transação apagada com sucesso!');
    } catch (err) {
        console.error(err);
        alert('❌ Erro ao apagar transação');
    }
}

async function carregarGraficoPizza() {
    try {
        const response = await fetch(`${API_BASE}/resumo?mes=${mesAtual}&ano=${anoAtual}`, {
            headers: getHeaders()
        });
        if (!response.ok) throw new Error('Erro ao carregar resumo');
        const data = await response.json();
        
        const ctx = document.getElementById('categoriaChart').getContext('2d');
        if (window.pizzaChart) {
            window.pizzaChart.destroy();
        }
        
        const cores = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#C9CBCF'];
        const labels = data.categorias.map(c => c.nome);
        const valores = data.categorias.map(c => c.valor);
        
        if (valores.reduce((a, b) => a + b, 0) === 0) {
            const parent = document.getElementById('categoriaChart').parentElement;
            parent.innerHTML = '<p class="text-center text-muted">Nenhum dado para exibir</p>';
            return;
        }
        
        window.pizzaChart = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: valores,
                    backgroundColor: cores.slice(0, labels.length)
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'bottom' }
                }
            }
        });
    } catch (err) {
        console.error(err);
        if (err.message.includes('401')) logout();
    }
}

async function carregarGraficoEvolucao() {
    try {
        const response = await fetch(`${API_BASE}/evolucao`, { headers: getHeaders() });
        if (!response.ok) throw new Error('Erro ao carregar evolução');
        const data = await response.json();
        
        const ctx = document.getElementById('evolucaoChart').getContext('2d');
        if (window.evolucaoChart && typeof window.evolucaoChart.destroy === 'function') {
            window.evolucaoChart.destroy();
        }
        
        const meses = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'];
        const labels = data.meses.map(m => {
            const [ano, mes] = m.split('-');
            return `${meses[parseInt(mes)-1]}/${ano}`;
        });
        
        window.evolucaoChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Receitas',
                        data: data.receitas,
                        borderColor: '#28a745',
                        backgroundColor: 'rgba(40,167,69,0.1)',
                        fill: true
                    },
                    {
                        label: 'Despesas',
                        data: data.despesas,
                        borderColor: '#dc3545',
                        backgroundColor: 'rgba(220,53,69,0.1)',
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'top' }
                },
                scales: {
                    y: { beginAtZero: true }
                }
            }
        });
    } catch (err) {
        console.error(err);
        if (err.message.includes('401')) logout();
    }
}

async function carregarMeses() {
    try {
        const response = await fetch(`${API_BASE}/transacoes?mes=${mesAtual}&ano=${anoAtual}`, {
            headers: getHeaders()
        });
        if (!response.ok) throw new Error('Erro ao carregar meses');
        const transacoes = await response.json();
        
        const mesesSet = new Set();
        transacoes.forEach(t => {
            const [dia, mes, ano] = t.data.split('/');
            mesesSet.add(`${mes}/${ano}`);
        });
        
        const select = document.getElementById('filtroMes');
        select.innerHTML = '';
        const mesesArray = Array.from(mesesSet).sort((a, b) => {
            const [mesA, anoA] = a.split('/');
            const [mesB, anoB] = b.split('/');
            return parseInt(anoA) - parseInt(anoB) || parseInt(mesA) - parseInt(mesB);
        });
        mesesArray.forEach(m => {
            const option = document.createElement('option');
            option.value = m;
            option.textContent = m;
            select.appendChild(option);
        });
        
        select.value = `${String(mesAtual).padStart(2,'0')}/${anoAtual}`;
        
        select.addEventListener('change', (e) => {
            const [mes, ano] = e.target.value.split('/');
            mesAtual = parseInt(mes);
            anoAtual = parseInt(ano);
            carregarDados();
        });
    } catch (err) {
        console.error(err);
        if (err.message.includes('401')) logout();
    }
}

async function carregarDados() {
    await carregarResumo();
    await carregarTransacoes();
    await carregarGraficoPizza();
    await carregarGraficoEvolucao();
    await carregarMeses();
    await carregarCategorias();
}

function init() {
    if (!token) {
        window.location.href = '/login';
        return;
    }
    
    document.getElementById('userName').textContent = usuario.nome || usuario.email;
    document.getElementById('mesAtual').textContent = `${String(mesAtual).padStart(2,'0')}/${anoAtual}`;
    document.getElementById('logoutBtn').addEventListener('click', logout);
    
    document.getElementById('filtroForma').addEventListener('change', (e) => {
        filtros.forma_pagamento = e.target.value;
        carregarDados();
    });
    document.getElementById('filtroTipo').addEventListener('change', (e) => {
        filtros.tipo = e.target.value;
        carregarDados();
    });
    
    document.getElementById('saveEditBtn').addEventListener('click', salvarEdicao);
    
    carregarDados();
}

document.addEventListener('DOMContentLoaded', init);
