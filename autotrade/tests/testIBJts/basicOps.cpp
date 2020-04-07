#define CATCH_CONFIG_MAIN

#include <boost/date_time.hpp>
#include <fstream>

#include "../catch.h"
#include "../../thirdparty/IBJts/DefaultEWrapper.h"
#include "../../thirdparty/IBJts/EClientSocket.h"
#include "../../thirdparty/IBJts/EReaderOSSignal.h"
#include "../../thirdparty/IBJts/EReader.h"

TEST_CASE("Establish connection", "[basic]") {
    // receives the responses
    DefaultEWrapper ePaperWrapper;
    DefaultEWrapper eRealWrapper;

    // signals message ready for processing in the queue
    EReaderOSSignal ePaperReaderSignal;
    EReaderOSSignal eRealReaderSignal;

    // sends messages to TWS
    EClientSocket ePaperCSocket(&ePaperWrapper, &ePaperReaderSignal);
    EClientSocket eRealCSocket(&eRealWrapper, &eRealReaderSignal);

    bool bPaperRes = ePaperCSocket.eConnect("", 7497, 0, false);
    bool bRealRes = eRealCSocket.eConnect("", 7496, 0, false);

    REQUIRE(bPaperRes != bRealRes);
}

TEST_CASE("Receive next valid ID", "[basic][reader]") {
    class IdWrapper : public DefaultEWrapper {
    public:
        OrderId orderId;

        IdWrapper() : orderId(-1) {}

        void nextValidId(OrderId validId) override {
            orderId = validId;
        }
    };

    IdWrapper idWrapper;
    EReaderOSSignal eSignal;
    EClientSocket eClient(&idWrapper, &eSignal);

    eClient.eConnect("", 7497, 0, false);

    EReader eReader(&eClient, &eSignal);

    eReader.start();
    eSignal.waitForSignal();
    eReader.processMsgs();

    REQUIRE(idWrapper.orderId != -1);
}

Contract spyContract() {
    Contract contract;
    contract.symbol = "SPY";
    contract.secType = "STK";
    contract.currency = "USD";
    contract.exchange = "SMART";

    return contract;
}

TEST_CASE("Receive 3 data points for SPY", "[basic][reader]") {
    // TODO: add check for day of the week and time.

    std::vector<double> prices;

    class MktDataWrapper : public DefaultEWrapper {
    public:
        OrderId orderId;
        std::vector<double> *priceList_;

        explicit MktDataWrapper(std::vector<double> *priceList) : orderId(-1) {
            priceList_ = priceList;
        }

        void nextValidId(OrderId validId) override {
            orderId = validId;
        }

        void tickPrice(
                TickerId tickerId,
                TickType field,
                double price,
                const TickAttrib &attribs
        ) override {
            priceList_->push_back(price);
        }
    };

    MktDataWrapper dataWrapper(&prices);
    EReaderOSSignal eSignal;
    EClientSocket eClient(&dataWrapper, &eSignal);

    eClient.eConnect("", 7497, 0, false);

    EReader eReader(&eClient, &eSignal);
    eReader.start();

    bool requestSent = false;
    while (true) {
        eSignal.waitForSignal();
        eReader.processMsgs();


        if (dataWrapper.orderId != -1 && !requestSent) {
            Contract contract = spyContract();
            eClient.reqMarketDataType(4);
            eClient.reqMktData(
                    dataWrapper.orderId + 20,
                    contract,
                    "",
                    false,
                    false,
                    TagValueListSPtr()
            );
            requestSent = true;
        }

        if (prices.size() > 3) {
            break;
        }
    }

    // TODO: fix this test case...
    REQUIRE(prices.size() > 3);
}

TEST_CASE("Get scanner params", "[basic][reader]") {
    class ScannerWrapper : public DefaultEWrapper {
    public:
        OrderId orderId;

        explicit ScannerWrapper() : orderId(-1) {}

        void nextValidId(OrderId validId) override {
            orderId = validId;
        }

        void scannerParameters(const std::string& xml) override {
            std::ofstream outputFile;
            outputFile.open("scanner_params.txt");
            outputFile << xml;
            outputFile.close();
        }
    };

    ScannerWrapper dataWrapper;
    EReaderOSSignal eSignal;
    EClientSocket eClient(&dataWrapper, &eSignal);

    eClient.eConnect("", 7497, 0, false);

    EReader eReader(&eClient, &eSignal);

    eReader.start();
    eSignal.waitForSignal();
    eReader.processMsgs();

    eClient.reqScannerParameters();
    eSignal.waitForSignal();
    eReader.processMsgs();
}
