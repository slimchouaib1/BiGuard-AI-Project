import React from 'react';

const Home = ({ user }) => (
  <>
    {/* Header */}
    <header className="sticky top-0 z-50 w-full border-b bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/60">
      <div className="container mx-auto flex h-16 items-center justify-between px-4 md:px-6">
        <div className="flex items-center space-x-2">
          <svg className="h-8 w-8 text-[#FF6A00]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
          <span className="text-2xl font-bold text-[#333333]">BiGuard</span>
        </div>
        {/* Desktop Navigation */}
        <nav className="hidden md:flex items-center space-x-8">
          <a href="#home" className="text-[#333333] hover:text-[#FF6A00] transition-colors">Home</a>
          <a href="#features" className="text-[#333333] hover:text-[#FF6A00] transition-colors">Features</a>
          <a href="#about" className="text-[#333333] hover:text-[#FF6A00] transition-colors">About Us</a>
          <a href="#contact" className="text-[#333333] hover:text-[#FF6A00] transition-colors">Contact</a>
        </nav>
        <div className="hidden md:flex items-center space-x-4">
          {user ? (
            <>
              <a href="/dashboard" className="text-[#333333] hover:text-[#FF6A00]">Dashboard</a>
              <button className="bg-[#FF6A00] hover:bg-[#E55A00] text-white px-4 py-2 rounded-lg">Logout</button>
            </>
          ) : (
            <>
              <a href="/login" className="text-[#333333] hover:text-[#FF6A00]">Login</a>
              <a href="/signup" className="bg-[#FF6A00] hover:bg-[#E55A00] text-white px-4 py-2 rounded-lg">Sign Up</a>
            </>
          )}
        </div>
      </div>
    </header>
    {/* Hero Section */}
    <section id="home" className="w-full py-12 md:py-24 lg:py-32 xl:py-48">
      <div className="container mx-auto px-4 md:px-6">
        <div className="grid gap-6 lg:grid-cols-[1fr_400px] lg:gap-12 xl:grid-cols-[1fr_600px]">
          <div className="flex flex-col justify-center space-y-4">
            <div className="space-y-2">
              <h1 className="text-3xl font-bold tracking-tighter sm:text-5xl xl:text-6xl/none text-[#333333]">
                Your Personal Finance Assistant, Powered by AI
              </h1>
              <p className="max-w-[600px] text-gray-600 md:text-xl">
                Track, Manage, and Secure Your Finances in Real-Time
              </p>
            </div>
            <div className="flex flex-col gap-2 min-[400px]:flex-row">
              <a href="/signup" className="bg-[#FF6A00] hover:bg-[#E55A00] text-white px-8 py-3 rounded-lg text-lg font-medium inline-block text-center">
                Get Started
              </a>
              <button className="border-2 border-[#FF6A00] text-[#FF6A00] hover:bg-[#FF6A00] hover:text-white px-8 py-3 rounded-lg text-lg font-medium">
                Learn More
              </button>
            </div>
          </div>
          <div className="flex items-center justify-center">
            <div className="relative">
              <img src="/placeholder.svg" alt="BiGuard App Dashboard" className="mx-auto aspect-video overflow-hidden rounded-xl object-cover shadow-2xl" />
              <div className="absolute inset-0 bg-gradient-to-tr from-[#FF6A00]/20 to-transparent rounded-xl"></div>
            </div>
          </div>
        </div>
      </div>
    </section>
    {/* Features Section */}
    <section id="features" className="w-full py-12 md:py-24 lg:py-32 bg-gray-50">
      <div className="container mx-auto px-4 md:px-6">
        <div className="flex flex-col items-center justify-center space-y-4 text-center">
          <div className="space-y-2">
            <h2 className="text-3xl font-bold tracking-tighter sm:text-5xl text-[#333333]">
              Powerful Features for Your Financial Security
            </h2>
            <p className="max-w-[900px] text-gray-600 md:text-xl/relaxed lg:text-base/relaxed xl:text-xl/relaxed">
              BiGuard combines cutting-edge AI technology with intuitive design to give you complete control over your finances.
            </p>
          </div>
        </div>
        <div className="mx-auto grid max-w-5xl items-center gap-6 py-12 lg:grid-cols-2 lg:gap-12">
          {/* Feature Cards */}
          <div className="bg-white p-6 rounded-xl shadow-lg hover:scale-105 transition-transform">
            <div className="flex flex-col items-center space-y-4 text-center">
              <svg className="h-12 w-12 text-[#FF6A00]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
              </svg>
              <h3 className="text-xl font-bold text-[#333333]">Expense Tracking</h3>
              <p className="text-gray-600">Track your spending with easy-to-read reports and charts. Get detailed insights into your financial habits.</p>
            </div>
          </div>
          <div className="bg-white p-6 rounded-xl shadow-lg hover:scale-105 transition-transform">
            <div className="flex flex-col items-center space-y-4 text-center">
              <svg className="h-12 w-12 text-[#FF6A00]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              <h3 className="text-xl font-bold text-[#333333]">Budget Management</h3>
              <p className="text-gray-600">Set personal budgets and get smart savings suggestions. Stay on track with your financial goals.</p>
            </div>
          </div>
          <div className="bg-white p-6 rounded-xl shadow-lg hover:scale-105 transition-transform">
            <div className="flex flex-col items-center space-y-4 text-center">
              <svg className="h-12 w-12 text-[#FF6A00]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
              <h3 className="text-xl font-bold text-[#333333]">Fraud Detection</h3>
              <p className="text-gray-600">Receive real-time alerts for suspicious activity in your transactions. Your security is our priority.</p>
            </div>
          </div>
          <div className="bg-white p-6 rounded-xl shadow-lg hover:scale-105 transition-transform">
            <div className="flex flex-col items-center space-y-4 text-center">
              <svg className="h-12 w-12 text-[#FF6A00]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <h3 className="text-xl font-bold text-[#333333]">Real-time Alerts</h3>
              <p className="text-gray-600">Get instant notifications about important financial activities and potential security threats.</p>
            </div>
          </div>
        </div>
      </div>
    </section>
    {/* CTA Section */}
    <section className="w-full py-12 md:py-24 lg:py-32 bg-gradient-to-r from-[#FF6A00] to-[#E55A00]">
      <div className="container mx-auto px-4 md:px-6">
        <div className="flex flex-col items-center justify-center space-y-4 text-center">
          <div className="space-y-2">
            <h2 className="text-3xl font-bold tracking-tighter sm:text-5xl text-white">
              Ready to Take Control of Your Finances?
            </h2>
            <p className="max-w-[600px] text-white/90 md:text-xl">
              Join thousands of users who trust BiGuard to protect and manage their financial future.
            </p>
          </div>
          <div className="flex flex-col gap-2 min-[400px]:flex-row">
            <a href="/signup" className="bg-white text-[#FF6A00] hover:bg-gray-100 px-8 py-3 rounded-lg text-lg font-medium inline-block text-center">
              Sign Up Now
            </a>
            <button className="border-2 border-white text-white hover:bg-white hover:text-[#FF6A00] px-8 py-3 rounded-lg text-lg font-medium">
              Contact Sales
            </button>
          </div>
        </div>
      </div>
    </section>
    {/* Footer */}
    <footer className="w-full py-6 border-t bg-white">
      <div className="container mx-auto px-4 md:px-6">
        <div className="grid gap-8 lg:grid-cols-4">
          <div className="flex flex-col space-y-4">
            <div className="flex items-center space-x-2">
              <svg className="h-6 w-6 text-[#FF6A00]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
              <span className="text-xl font-bold text-[#333333]">BiGuard</span>
            </div>
            <p className="text-sm text-gray-600">Your trusted personal finance assistant, powered by AI technology.</p>
          </div>
          <div className="flex flex-col space-y-4">
            <h3 className="text-lg font-semibold text-[#333333]">Product</h3>
            <div className="flex flex-col space-y-2">
              <a href="#features" className="text-sm text-gray-600 hover:text-[#FF6A00]">Features</a>
              <a href="#" className="text-sm text-gray-600 hover:text-[#FF6A00]">Pricing</a>
              <a href="#" className="text-sm text-gray-600 hover:text-[#FF6A00]">Security</a>
            </div>
          </div>
          <div className="flex flex-col space-y-4">
            <h3 className="text-lg font-semibold text-[#333333]">Company</h3>
            <div className="flex flex-col space-y-2">
              <a href="#about" className="text-sm text-gray-600 hover:text-[#FF6A00]">About Us</a>
              <a href="#contact" className="text-sm text-gray-600 hover:text-[#FF6A00]">Contact</a>
              <a href="#" className="text-sm text-gray-600 hover:text-[#FF6A00]">Careers</a>
            </div>
          </div>
          <div className="flex flex-col space-y-4">
            <h3 className="text-lg font-semibold text-[#333333]">Legal</h3>
            <div className="flex flex-col space-y-2">
              <a href="#" className="text-sm text-gray-600 hover:text-[#FF6A00]">Terms of Service</a>
              <a href="#" className="text-sm text-gray-600 hover:text-[#FF6A00]">Privacy Policy</a>
              <a href="#" className="text-sm text-gray-600 hover:text-[#FF6A00]">Cookie Policy</a>
            </div>
          </div>
        </div>
        <div className="flex flex-col sm:flex-row justify-between items-center pt-8 mt-8 border-t">
          <p className="text-xs text-gray-600">© 2025 BiGuard. All rights reserved.</p>
        </div>
      </div>
    </footer>
  </>
);

export default Home; 