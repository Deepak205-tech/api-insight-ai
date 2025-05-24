import React, { useState } from 'react';
import axios from 'axios';
import { Spinner } from "./components/ui/spinner";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";
import { AuroraText } from "./components/ui/aurora-text";
import { TextAnimate } from "./components/ui/text-animate";
import { RainbowButton } from "./components/ui/rainbow-button";

function App() {
  const [apiSpec, setApiSpec] = useState('');
  const [testCases, setTestCases] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeCategory, setActiveCategory] = useState(null);

  const categoryPrompts = {
    positive: 'Generate only positive test cases for this API endpoint. Return ONLY a valid JSON array of positive test cases as described in the previous format. Do not include any other categories or explanations.',
    negative: 'Generate only negative test cases for this API endpoint. Return ONLY a valid JSON array of negative test cases as described in the previous format. Do not include any other categories or explanations.',
    edge: 'Generate only edge test cases for this API endpoint. Return ONLY a valid JSON array of edge test cases as described in the previous format. Do not include any other categories or explanations.',
    security: 'Generate only security test cases for this API endpoint. Return ONLY a valid JSON array of security test cases as described in the previous format. Do not include any other categories or explanations.'
  };

  const generateCategoryTests = async (category) => {
    setLoading(true);
    setTestCases(null);
    setActiveCategory(category);
    try {
      const endpoints = apiSpec.split('\n').map(e => e.trim()).filter(Boolean);
      if (endpoints.length === 0) return;
      const endpoint = endpoints[0];
      const prompt = `${endpoint}\n${categoryPrompts[category]}`;
      const response = await axios.post('http://localhost:8000/analyze-api', {
        endpoints: [prompt]
      });
      if (response.data.error) {
        console.error('Error:', response.data.error);
        setTestCases(null);
        return;
      }
      let parsedTestCases;
      // Always parse the string if needed
      let tc = response.data.testcases;
      if (typeof tc === 'string') {
        try {
          tc = JSON.parse(tc);
        } catch (e) {
          console.error('Failed to parse testcases string:', e);
          setTestCases([{ raw_response: response.data.testcases }]);
          setLoading(false);
          return;
        }
      }
      // If tc is an object with category arrays, extract the correct one
      if (tc && typeof tc === 'object' && !Array.isArray(tc) && Array.isArray(tc[category + '_tests'])) {
        parsedTestCases = tc[category + '_tests'];
      } else if (Array.isArray(tc)) {
        parsedTestCases = tc;
      } else {
        parsedTestCases = [];
      }
      setTestCases(parsedTestCases);
    } catch (error) {
      console.error('Error generating tests:', error);
      setTestCases(null);
    } finally {
      setLoading(false);
    }
  };

  const TestCaseTable = ({ title, testCases }) => {
    if (!testCases || testCases.length === 0) return null;

    const formatValue = (value) => {
      if (typeof value === 'object') {
        return <pre className="text-xs text-green-400">{JSON.stringify(value, null, 2)}</pre>;
      }
      return value;
    };

    return (
      <div className="mb-8">
        <h3 className="text-xl font-bold mb-3 text-white">{title}</h3>
        <div className="bg-gray-900 rounded-lg shadow p-4 overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-700">
            <thead className="bg-gray-800">
              <tr>
                {["#", "URL", "Method", "Headers", "Request Body", "Expected Status", "Expected Response", "Description"].map((head, idx) => (
                  <th key={idx} className="px-4 py-2 text-left text-xs font-bold text-gray-300 uppercase tracking-wider">{head}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {testCases.map((test, idx) => (
                <tr key={idx} className="hover:bg-gray-800 transition">
                  <td className="px-4 py-2 text-sm text-gray-200 font-semibold">{idx + 1}</td>
                  <td className="px-4 py-2 text-sm text-blue-400 truncate max-w-xs" title={test.request_url}>{test.request_url || 'N/A'}</td>
                  <td className="px-4 py-2 text-sm text-green-400">{test.http_method || 'N/A'}</td>
                  <td className="px-4 py-2 text-xs text-gray-300">{formatValue(test.headers)}</td>
                  <td className="px-4 py-2 text-xs text-gray-300">{formatValue(test.request_body)}</td>
                  <td className="px-4 py-2 text-sm text-yellow-300">{test.expected_response_code || 'N/A'}</td>
                  <td className="px-4 py-2 text-xs text-gray-300">{formatValue(test.expected_response_body)}</td>
                  <td className="px-4 py-2 text-xs text-gray-300">{test.description || 'N/A'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  // ErrorBoundary for TextAnimate
  class ErrorBoundary extends React.Component {
    constructor(props) {
      super(props);
      this.state = { hasError: false };
    }
    static getDerivedStateFromError(error) {
      return { hasError: true };
    }
    componentDidCatch(error, errorInfo) {
      // Optionally log error
      // console.error('ErrorBoundary caught:', error, errorInfo);
    }
    render() {
      if (this.state.hasError) {
        return (
          <div className="text-red-400 text-center text-lg font-bold py-8">
            Oops! Something went wrong with the animation.<br />
            Please try again or reload the page.
          </div>
        );
      }
      return this.props.children;
    }
  }

  return (
    <div className="min-h-screen bg-black py-8">
      <div className="max-w-5xl mx-auto px-4">
        <h1 className="text-5xl font-extrabold mb-10 tracking-tight">
          <AuroraText>API Insight AI</AuroraText>
        </h1>
        <Card className="bg-gray-900 border-none mb-8">
          <CardContent className="p-6">
            <div className="flex flex-col gap-4">
              <Textarea
                value={apiSpec}
                onChange={(e) => setApiSpec(e.target.value)}
                placeholder="Enter your API endpoint (e.g., GET /users)"
                className="bg-gray-800 text-white border-2 border-transparent focus:border-transparent focus:ring-4 focus:ring-green-400/60 w-full resize-none text-lg rounded-xl shadow-lg transition-all duration-300 outline-none [box-shadow:0_0_0_3px_rgba(34,211,238,0.4),0_2px_8px_rgba(0,0,0,0.15)] focus:[box-shadow:0_0_0_4px_rgba(34,211,238,0.7),0_2px_16px_rgba(0,0,0,0.18)]"
                disabled={loading}
                style={{ minHeight: '20vh', maxHeight: '60vh', height: 'auto', overflow: 'auto' }}
                rows={Math.max(6, apiSpec.split('\n').length)}
              />
              <div className="flex flex-row gap-4 w-full">
                <RainbowButton
                  onClick={() => generateCategoryTests('positive')}
                  className={`flex-1 py-4 text-lg font-bold text-white bg-gradient-to-r from-green-400 via-blue-500 to-purple-500 hover:from-green-500 hover:to-blue-600 transition-all duration-300 rounded-lg shadow-xl ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                  disabled={loading}
                  style={{ minHeight: 56, fontSize: 20 }}
                >
                  Positive
                </RainbowButton>
                <RainbowButton
                  onClick={() => generateCategoryTests('negative')}
                  className={`flex-1 py-4 text-lg font-bold text-white bg-gradient-to-r from-red-400 via-pink-500 to-purple-500 hover:from-red-500 hover:to-pink-600 transition-all duration-300 rounded-lg shadow-xl ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                  disabled={loading}
                  style={{ minHeight: 56, fontSize: 20 }}
                >
                  Negative
                </RainbowButton>
                <RainbowButton
                  onClick={() => generateCategoryTests('edge')}
                  className={`flex-1 py-4 text-lg font-bold text-white bg-gradient-to-r from-yellow-400 via-orange-500 to-pink-500 hover:from-yellow-500 hover:to-orange-600 transition-all duration-300 rounded-lg shadow-xl ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                  disabled={loading}
                  style={{ minHeight: 56, fontSize: 20 }}
                >
                  Edge
                </RainbowButton>
                <RainbowButton
                  onClick={() => generateCategoryTests('security')}
                  className={`flex-1 py-4 text-lg font-bold text-white bg-gradient-to-r from-blue-400 via-indigo-500 to-purple-500 hover:from-blue-500 hover:to-indigo-600 transition-all duration-300 rounded-lg shadow-xl ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                  disabled={loading}
                  style={{ minHeight: 56, fontSize: 20 }}
                >
                  Security
                </RainbowButton>
              </div>
            </div>
          </CardContent>
        </Card>
        {loading && (
          <ErrorBoundary>
            <div className="flex flex-col items-center justify-center py-20">
              <Spinner size={64} color="#22d3ee" className="mb-6" />
              <div className="text-xl font-semibold text-green-300 text-center mb-2">
                AI is generating your test cases...
              </div>
              <div className="text-2xl font-bold text-green-400 text-center">
                Unleashing the power of Mistral! 🦙✨
              </div>
            </div>
          </ErrorBoundary>
        )}
        {!loading && testCases && activeCategory && (
          <Card className="bg-gray-900 border-none">
            <CardContent className="p-6">
              <h2 className="text-3xl font-bold mb-6 text-white">{activeCategory.charAt(0).toUpperCase() + activeCategory.slice(1)} Test Cases</h2>
              <TestCaseTable title={activeCategory.charAt(0).toUpperCase() + activeCategory.slice(1) + ' Test Cases'} testCases={testCases} />
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

export default App;
