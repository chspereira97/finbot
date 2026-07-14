// ============================================================
// FinBot - Dashboard JavaScript
// ============================================================

const API_BASE = '/api';
let token = localStorage.getItem('token');
let usuario = JSON.parse(localStorage.getItem('usuario') || '{}');
let mesAtual = new Date().getMonth() + 1;
let anoAtual = new Date().getFullYear();

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
        const response = await fetch(`${API_BASE}/transacoes?mes=${mesAtual}&ano=${anoAtual}`, {
            headers: getHeaders()
        });
        if (!response.ok) throw new Error('Erro ao carregar transações');
        const transacoes = await response.json();
        
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
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error(err);
        if (err.message.includes('401')) logout();
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
        
        if (window.pizzaChart) window.pizzaChart.destroy();
        
        const cores = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40'];
        
        window.pizzaChart = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: data.categorias.map(c => c.nome),
                datasets: [{
                    data: data.categorias.map(c => c.valor),
                    backgroundColor: cores.slice(0, data.categorias.length)
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
        const response = await fetch(`${API_BASE}/evolucao`, {
            headers: getHeaders()
        });
        if (!response.ok) throw new Error('Erro ao carregar evolução');
        const data = await response.json();
        
        const ctx = document.getElementById('evolucaoChart').getContext('2d');
        
        if (window.evolucaoChart) window.evolucaoChart.destroy();
        
        const labels = data.meses.map(m => {
            const [ano, mes] = m.split('-');
            const meses = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'];
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
        const response = await fetch(`${API_BASE}/transacoes`, {
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

// ============================================================
// INICIALIZAÇÃO
// ============================================================

async function carregarDados() {
    await carregarResumo();
    await carregarTransacoes();
    await carregarGraficoPizza();
    await carregarGraficoEvolucao();
    await carregarMeses();
}

function init() {
    if (!token) {
        window.location.href = '/login';
        return;
    }
    
    document.getElementById('userName').textContent = usuario.nome || usuario.email;
    document.getElementById('mesAtual').textContent = `${String(mesAtual).padStart(2,'0')}/${anoAtual}`;
    document.getElementById('logoutBtn').addEventListener('click', logout);
    
    carregarDados();
}

document.addEventListener('DOMContentLoaded', init);
